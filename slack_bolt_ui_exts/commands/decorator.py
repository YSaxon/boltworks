import argparse
import copy
import inspect
import shlex
import typing
from typing import Optional, Union

import makefun
import slack_bolt.kwargs_injection.args

NoneType = type(None)


class SlackArgParseFormatter(argparse.HelpFormatter):
    def __init__(self, prog):
        super(SlackArgParseFormatter, self).__init__(
            prog,
            # max_help_position=55,
            width=80,
        )


possible_slack_args = list(slack_bolt.kwargs_injection.args.Args.__annotations__.keys())


def argparse_command(argparser:Optional[argparse.ArgumentParser]=None,echo_back=True,do_ack=True,automagic=False):
    if not argparser:
        if not automagic:
            raise ValueError("If you don't pass in an argparser, you must set automagic to True")
        argparser=argparse.ArgumentParser()

    argparser_dests=[a.dest for a in argparser._actions if a.dest !="help"]
    argname_conflicts=[dest for dest in argparser_dests if dest in possible_slack_args]
    if argname_conflicts:
        raise ValueError(f"One or more dest param names in your argparser conflict with built in param names used by slack bolt: {', '.join(argname_conflicts)}\nTry setting the `dest` argument in your argparser action to something else")
    def _mid_func(decorated_function):
        midfunc_argparser=argparser
        deco_sig=inspect.signature(decorated_function)
        deco_argnames=[a.name for a in deco_sig.parameters.values()]

        deco_varargs=[a.name for a in deco_sig.parameters.values() if a.kind==a.VAR_POSITIONAL]
        if deco_varargs:
            raise ValueError(f"There is a varargs `*{deco_varargs[0]}` in the method signature of the method you are decorating, which is unsupported. Please use a list instead")

        deco_varkwargs=[a.name for a in deco_sig.parameters.values() if a.kind==a.VAR_KEYWORD]
        if not deco_varkwargs: #if there is no **kwargs to handle extra arguments...
            unhandled_arguments=[dest for dest in argparser_dests
                                 if dest not in deco_argnames]
            if unhandled_arguments:
                raise ValueError(f"The argparser object you provided generates one or more arguments ({','.join(unhandled_arguments)}) which are unhandled by the method you are decorating, nor does your method does not have a **kwargs to absorb them")


        deco_extra_args_in_deco=[a for a in deco_sig.parameters.values()
                                                  if a.kind is not a.VAR_KEYWORD
                                                  and a.name not in possible_slack_args
                                                  and a.name not in argparser_dests]
        deco_extra_args_in_deco_without_defaults=[a for a in deco_extra_args_in_deco if a.default is a.empty]
        if not automagic and deco_extra_args_in_deco_without_defaults:
            raise ValueError(f"The method you are decorating has one or more parameters without defaults defined that your argparser is not set to fill and are not slack bolt arguments:{','.join(deco_extra_args_in_deco)}")
        if automagic and deco_extra_args_in_deco:
            midfunc_argparser = automagically_add_args_to_argparser(decorated_function, midfunc_argparser, deco_extra_args_in_deco)

        def _inner_func_to_return_to_slack(command,respond,ack,say,context,**other_slackvars):
            def fn(message,file=None):
                respond(text="```"+message+"```")
                ack()
            innerfunc_argparser=copy.deepcopy(midfunc_argparser)#so we can have _print_message be unique to each call
            innerfunc_argparser.formatter_class=SlackArgParseFormatter
            innerfunc_argparser._print_message=fn


            command['text']=command['text'] if 'text' in command else ''
            # command['text']=unmark(command['text'])# this was an attempt to remove markup formatting but failed because inherently impossible to do reliably
            # whenever they add 'blocks' to the command response, we can parse that to get the exact plaintext representation
            # see also https://stackoverflow.com/a/70627214/10773089
            args_split=shlex.split(command['text'])
            innerfunc_argparser.prog=command['command'] if 'command' in command else '<cmd>'
            parsed_params=vars(innerfunc_argparser.parse_args(args_split))

            if do_ack:
                ack()
            if echo_back:
                say(text=f"*{command['command']} {(command['text'] if command['text'] else '')}*  \t(run by <@{context['user_id']}>)")

            possible_slackvars_to_pass=dict(command=command,respond=respond,ack=ack,say=say,context=context,**other_slackvars)

            vars_to_pass={k:v for k,v in possible_slackvars_to_pass.items() if not (k in possible_slack_args and k not in deco_argnames)}#filter out slackvars the decorated func doesn't want
            vars_to_pass.update(parsed_params)#note that if somehow there is still a conflict between argparser and slack vars, argparser will win out at this stage
            return decorated_function(**vars_to_pass)

        inner_sig=inspect.signature(_inner_func_to_return_to_slack)
        all_inner_but_final_varkwargs=list(inner_sig.parameters.values())[:-1] #or else maybe filter out varkwargs?
        aibfv_names=[p.name for p in all_inner_but_final_varkwargs]
        # we could possibly just make that a static list aibfv_names=["command","respond","ack","say","context"]

        slack_params_to_add_from_decorated_func=[p for p in deco_sig.parameters.values() if p.name in possible_slack_args and p.name not in aibfv_names]
        signature_for_slack=deco_sig.replace(parameters=all_inner_but_final_varkwargs+slack_params_to_add_from_decorated_func)
        func_to_return_to_slack=makefun.create_function(signature_for_slack,_inner_func_to_return_to_slack,decorated_function.__name__)

        return func_to_return_to_slack

    #on init, it will return a function that does all the above stuff when run
    return _mid_func
#could potentially extend further to do the app.command command wrapper as well and maybe even handle making the regex string too


def automagically_add_args_to_argparser(decorated_function, midfunc_argparser, deco_extra_args_in_deco):
        supported_simple_types=[str,int,float,bool]
        midfunc_argparser=copy.deepcopy(midfunc_argparser)#in case the same argparser is reused for other methods we don't want to pollute it
        type_hints=typing.get_type_hints(decorated_function)
        for arg in deco_extra_args_in_deco:
            arg_default = arg.default if arg.default is not arg.empty else None
            if arg.name not in type_hints:
                if not type(arg_default) in supported_simple_types:#which should also helpfully catch if the arg_default == None, or a typeless list, in which case we can't infer type from it
                    raise ValueError(f"The method you are decorating has a parameter `{arg.name}` not filled by slack or the argparser you provided, and we can't automagically extend your argparser because the parameter does not have a type hint, nor does it have a default value whose type we can easily infer")
                nargs=None
                ultimate_type=type(arg_default)
            else:
                arg_type=type_hints[arg.name]
                arg_type_generic_parent_type=typing.get_origin(arg_type)
                is_simple_type=arg_type in supported_simple_types
                is_generic_type=arg_type_generic_parent_type in [list,Union]
                type_error_message=f"The method you are decorating has a parameter `{arg.name}` not filled by slack or the argparser you provided, and we can't automagically extend your argparser because the parameter's type hint is {arg_type} rather than one of the following Supported Types: {','.join([str(t) for t in supported_simple_types])}, or an Optional[SupportedType], list[SupportedType], or Optional[list[SupportedType]]"
                if not is_simple_type and not is_generic_type:#optional type ends up as Union, but we don't officially support Union
                    raise ValueError(type_error_message)
                if is_simple_type:
                    nargs=None #exactly one
                    ultimate_type=arg_type
                else:
                    arg_type_subtypes=typing.get_args(arg_type)
                    if arg_type_generic_parent_type is list:
                        if not len(arg_type_subtypes)==1 \
                                or not arg_type_subtypes[0] in supported_simple_types:
                            raise ValueError(type_error_message)#ValueError(f"The method you are decorating has a parameter `{arg}` not filled by slack or the argparser you provided, and we can't automagically extend your argparser because the parameter's type hint is a list not annotated by a single subtype in: {','.join(supported_simple_types)}")
                        nargs="+"
                        ultimate_type=arg_type_subtypes[0]
                    elif arg_type_generic_parent_type is Union:
                        if not len(arg_type_subtypes)==2 or not type(None) in arg_type_subtypes:
                            raise ValueError(type_error_message)
                        subtype_of_optional=arg_type_subtypes[0] if arg_type_subtypes[1] is type(None) else arg_type_subtypes[1]
                        if subtype_of_optional in supported_simple_types:
                            nargs="?"
                            ultimate_type=subtype_of_optional
                        else:
                            double_subtypes=typing.get_args(subtype_of_optional)
                            if not typing.get_origin(subtype_of_optional) is list \
                                        or not len(double_subtypes)==1\
                                        or not double_subtypes[0] in supported_simple_types:
                                raise ValueError(type_error_message)
                            nargs="*"
                            ultimate_type=double_subtypes[0]
            if arg_default:#because otherwise the default won't actually work
                if nargs=="+":
                    nargs="*"
                elif nargs is None:
                    nargs="?"
            arg_type_str=str(arg_type).removeprefix("typing.").removeprefix("<class '").removesuffix("'>").rstrip("]").replace("list[", "list of ").replace("Optional[", "(optional) ")
            midfunc_argparser.add_argument(arg.name if not arg.kind==arg.KEYWORD_ONLY else f"--{arg.name}",nargs=nargs,type=ultimate_type,default=arg_default,help=f'{arg_type_str}{f", default: {arg_default}" if arg_default else ""}')
        return midfunc_argparser
