import argparse
import copy
import inspect
import shlex

import makefun
import slack_bolt.kwargs_injection.args


class SlackArgParseFormatter(argparse.HelpFormatter):
    def __init__(self, prog):
        super(SlackArgParseFormatter, self).__init__(
            prog,
            # max_help_position=55,
            width=80,
        )


possible_slack_args = list(slack_bolt.kwargs_injection.args.Args.__annotations__.keys())


def argparse_command(argparser: argparse.ArgumentParser, echo_back=True, do_ack=True):
    argparser_dests = [a.dest for a in argparser._actions if a.dest != "help"]
    argname_conflicts = [
        dest for dest in argparser_dests if dest in possible_slack_args
    ]
    if argname_conflicts:
        raise ValueError(
            f"One or more dest param names in your argparser conflict with built in param names used by slack bolt: {', '.join(argname_conflicts)}\nTry setting the `dest` argument in your argparser action to something else"
        )

    def _mid_func(decorated_function):

        deco_sig = inspect.signature(decorated_function)
        deco_argnames = [a.name for a in deco_sig.parameters.values()]

        deco_varargs = [
            a.name for a in deco_sig.parameters.values() if a.kind == a.VAR_POSITIONAL
        ]
        if deco_varargs:
            raise ValueError(
                f"There is a varargs `*{deco_varargs[0]}` in the method signature of the method you are decorating, which is unsupported. Please use a list instead"
            )

        deco_varkwargs = [
            a.name for a in deco_sig.parameters.values() if a.kind == a.VAR_KEYWORD
        ]
        if not deco_varkwargs:  # if there is no **kwargs to handle extra arguments...
            unhandled_arguments = [
                dest for dest in argparser_dests if dest not in deco_argnames
            ]
            if unhandled_arguments:
                raise ValueError(
                    f"The argparser object you provided generates one or more arguments ({','.join(unhandled_arguments)}) which are unhandled by the method you are decorating, nor does your method does not have a **kwargs to absorb them"
                )

        deco_extra_args_in_deco_without_defaults = [
            a.name
            for a in deco_sig.parameters.values()
            if a.kind is not a.VAR_KEYWORD
            and a.default is a.empty
            and a.name not in possible_slack_args
            and a.name not in argparser_dests
        ]
        if deco_extra_args_in_deco_without_defaults:
            raise ValueError(
                f"The method you are decorating has one or more parameters without defaults defined that your argparser is not set to fill and are not slack bolt arguments:{','.join(deco_extra_args_in_deco_without_defaults)}"
            )

        def _inner_func_to_return_to_slack(
            command, respond, ack, say, context, **other_slackvars
        ):
            def fn(message, file=None):
                respond(text="```" + message + "```")
                ack()

            arg_parser = copy.deepcopy(
                argparser
            )  # so we can have _print_message be unique to each call
            arg_parser.formatter_class = SlackArgParseFormatter
            arg_parser._print_message = fn

            command["text"] = command["text"] if "text" in command else ""
            # command['text']=unmark(command['text'])# this was an attempt to remove markup formatting but failed because inherently impossible to do reliably
            # whenever they add 'blocks' to the command response, we can parse that to get the exact plaintext representation
            # see also https://stackoverflow.com/a/70627214/10773089
            args_split = shlex.split(command["text"])
            arg_parser.prog = command["command"] if "command" in command else "<cmd>"
            parsed_params = vars(arg_parser.parse_args(args_split))

            if do_ack:
                ack()
            if echo_back:
                say(
                    text=f"*{command['command']} {(command['text'] if command['text'] else '')}*    (run by <@{context['user_id']}>)"
                )

            possible_slackvars_to_pass = dict(
                command=command,
                respond=respond,
                ack=ack,
                say=say,
                context=context,
                **other_slackvars,
            )

            vars_to_pass = {
                k: v
                for k, v in possible_slackvars_to_pass.items()
                if not (k in possible_slack_args and k not in deco_argnames)
            }  # filter out slackvars the decorated func doesn't want
            vars_to_pass.update(
                parsed_params
            )  # note that if somehow there is still a conflict between argparser and slack vars, argparser will win out at this stage
            return decorated_function(**vars_to_pass)

        inner_sig = inspect.signature(_inner_func_to_return_to_slack)
        all_inner_but_final_varkwargs = list(inner_sig.parameters.values())[
            :-1
        ]  # or else maybe filter out varkwargs?
        aibfv_names = [p.name for p in all_inner_but_final_varkwargs]
        # we could possibly just make that a static list aibfv_names=["command","respond","ack","say","context"]

        slack_params_to_add_from_decorated_func = [
            p
            for p in deco_sig.parameters.values()
            if p.name in possible_slack_args and p.name not in aibfv_names
        ]
        signature_for_slack = deco_sig.replace(
            parameters=all_inner_but_final_varkwargs
            + slack_params_to_add_from_decorated_func
        )
        func_to_return_to_slack = makefun.create_function(
            signature_for_slack,
            _inner_func_to_return_to_slack,
            decorated_function.__name__,
        )

        return func_to_return_to_slack  # on init, it will return a function that does all the above stuff when run

    return _mid_func
