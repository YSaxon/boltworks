import argparse
from argparse import Action, ArgumentParser
import copy
import inspect
import shlex
import sys
import typing
from typing import Any, Literal, Optional, Union

from slack_bolt import Args
from ..helper.slack_utils import safe_post_in_blockquotes


NoneType = type(None)


class SlackArgParseFormatter(argparse.HelpFormatter):
    def __init__(self, prog):
        super(SlackArgParseFormatter, self).__init__(
            prog,
            # max_help_position=55,
            width=80,
        )

RESERVED_SLACK_ARGS = ["args",*Args.__annotations__.keys()]

def argparse_command(argparser:Optional[ArgumentParser]=None,echo_back=True,do_ack=True,automagic=False):
    """
    This is the primary method for this feature. It is a decorator that you put onto your Slack Command Method to parse the arguments in the command and pass them to your function.

    You can either construct an argparse.ArgumentParser yourself to do the work (better)
    Or set automagic=True to have a simple ArgumentParser constructed for you based on your method signature (faster)
    
    Any parameter names in your method signature which Slack would usually inject (eg 'args' or 'say' or 'logger' etc) will be passed through.
    
    ```
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--a", nargs="*", type=float)
    argparser.add_argument("-b", type=int)
    argparser.add_argument("c")
    argparser.add_argument("d", nargs="?", default="default")
    
    @app.command("/dothething")
    @argparse_command(parser)
    def your_method_name(args:Args, say, a, b, c, d):
        ...
    ```
    
    can be called as `/dothething cc dd --a 1 2 3 -b 5`
    
    In automagic mode, to have a parameter be called as --foo, make it KeywordOnly by placing it after a single asterisk. Otherwise the argument name is silent
    ```
    @app.command("/dotheotherthing")
    @argparse_command(automagic=True)
    def your_method_name(args:Args, say, a:str, b:list[int], *, c:int, d:int):
        ...
    ```
    can be called as `/dotheotherthing test 1 2 3 --d 6 --c 5`
    
    (You are allowed to use Automagic together with an ArgumentParser as well to fill in an extra arg not handled by the parser)
    
    
    In both cases, the argparser library will always insert a `--help` parameter, though it will be better documented if you build your own ArgumentParser.
    It's recommended when you configure the Command in Slack to configure the usage string as `[--help]` to let people know they can do that.
    
    Args:
        argparser (Optional[ArgumentParser]): An optional argparse.ArgumentParser object with which to parse the arguments
        echo_back (bool, optional): _description_. Defaults to True. Calls 'say' to echo back the command executed to the user before executing it.
        do_ack (bool, optional): _description_. Defaults to True. Calls Slack's ack() method for you upon succesful parsing, so you don't have to do it yourself.
        automagic (bool, optional): _description_. Defaults to False. Enables automagic parsing of arguments based on your method signature. Only supported on Python>=3.9

    Raises:
        ValueError: various ValueErrors can be raised, generally at the time of creation of the argparse_handler
        * If there are conflicts between slack-reserved argnames and your argparser names
        * If you don't have automagic set to True and don't pass an ArgumentParser, or the ArgumentParser doesn't handle all your method's params
        * If you use automagic, but don't sufficiently type-hint your parameters, or the types are too complicated etc.

    """  
    if not argparser:
        if not automagic:
            raise ValueError("If you don't pass in an argparser, you must set automagic to True")
        argparser=ArgumentParser()
        
    if automagic and sys.version_info < (3, 9):
        raise ValueError("automagic mode is not supported on Python versions < 3.9")

    argparser_dests=[a.dest for a in argparser._actions if a.dest !="help"]
    
    argname_conflicts=[dest for dest in argparser_dests if dest in RESERVED_SLACK_ARGS]
    if argname_conflicts:
        raise ValueError(f"One or more dest param names in your argparser conflict with built in param names used by slack bolt: {', '.join(argname_conflicts)}\nTry setting the `dest` argument for those argparser actions to something else")
    # if "args" in argparser_dests:
    #     raise ValueError(f"The 'args' param name is reserved for Slack, so you can't use it for an argparser argument name.\nTry setting `the` dest parameter for that action to something else")
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
                                                  and a.name not in RESERVED_SLACK_ARGS 
                                                  and a.name not in argparser_dests]
        deco_extra_args_in_deco_without_defaults=[a for a in deco_extra_args_in_deco if a.default is a.empty]
        if not automagic and deco_extra_args_in_deco_without_defaults:
            raise ValueError(f"The method you are decorating has one or more parameters without defaults defined that your argparser is not set to fill:{','.join(deco_extra_args_in_deco)}")
        if automagic and deco_extra_args_in_deco:
            midfunc_argparser = automagically_add_args_to_argparser(decorated_function, midfunc_argparser, deco_extra_args_in_deco)

        def _inner_func_to_return_to_slack(args:Args):
            def fn(message,file=None):
                safe_post_in_blockquotes(args.respond,message)
                args.ack()
            innerfunc_argparser=copy.deepcopy(midfunc_argparser)#so we can have _print_message be unique to each call
            innerfunc_argparser.formatter_class=SlackArgParseFormatter
            innerfunc_argparser._print_message=fn

            if args.command:
                command_base=args.command['command'].replace("*","") if 'command' in args.command else '<cmd>'
                command_args=shlex.split(args.command['text'].replace("*","")) if 'text' in args.command else []
            elif args.message:
                split_message=shlex.split(args.message['text'].replace("*",""))
                command_base=split_message[0]
                command_args=split_message[1:]
            else: raise Exception("This class is only to be used with @command or @message")

            # unfortunately it's not possible to perfectly strip out the markup formatting so for now we are just stripping out asterisks
            # whenever they add 'blocks' to the command response, we can parse that to get the exact plaintext representation
            # see also https://stackoverflow.com/a/70627214/10773089

            innerfunc_argparser.prog=command_base
            
            #maybe add more verbose explanation if you use `--var`` when it should have been `var`, or vice versa
            parsed_params=vars(innerfunc_argparser.parse_args(command_args))

            if do_ack:
                args.ack()
            if echo_back:
                args.say(text=f"*{command_base} {(shlex.join(command_args))}*  \t(run by <@{args.context['user_id']}>)")
            
            available_slackvars_to_pass={'args':args,**vars(args)}
            if deco_varkwargs:#if there's a varkwargs then just pass everything
                slackvars_to_pass=available_slackvars_to_pass
            else:
                slackvars_to_pass={k:v for k,v in available_slackvars_to_pass.items() if k in deco_argnames} 
            return decorated_function(**slackvars_to_pass,**parsed_params)
        return _inner_func_to_return_to_slack

    #on init, it will return a function that does all the above stuff when run
    return _mid_func
#could potentially extend further to do the app.command command wrapper as well and maybe even handle making the regex string too


def automagically_add_args_to_argparser(decorated_function, midfunc_argparser, deco_extra_args_in_deco):
        supported_simple_types=[str,int,float,bool]
        midfunc_argparser:ArgumentParser=copy.deepcopy(midfunc_argparser)#in case the same argparser is reused for other methods we don't want to pollute it
        type_hints=typing.get_type_hints(decorated_function)
        for arg in deco_extra_args_in_deco:
            arg_default = arg.default if arg.default is not arg.empty else None
            if arg.name not in type_hints:
                if not type(arg_default) in supported_simple_types:#which should also helpfully catch if the arg_default == None, or a typeless list, in which case we can't infer type from it
                    raise ValueError(f"Automagic failed, please add a type hint for `{arg.name}`.\nThe method you are decorating has a parameter `{arg.name}` not filled by slack or an argparser, and we can't automagically extend your argparser because the parameter does not have a type hint, nor does it have a default value whose type we can easily infer")
                nargs=None
                arg_type=type(arg_default)
                ultimate_type=type(arg_default)
            else:
                arg_type=type_hints[arg.name]
                arg_type_generic_parent_type=typing.get_origin(arg_type)
                is_simple_type=arg_type in supported_simple_types
                is_generic_type=arg_type_generic_parent_type in [list,Union,Literal]
                type_error_message=f"Automagic failed, please use an ArgumentParser for `{arg.name}` or use a simpler type.\nThe method you are decorating has a parameter `{arg.name}` not filled by slack or an argparser, and we can't automagically extend your argparser because the parameter's type hint is {arg_type} rather than one of the following supported types: {','.join([str(t) for t in supported_simple_types])}, or an Optional[SupportedType], list[SupportedType], or Optional[list[SupportedType]]"
                if not is_simple_type and not is_generic_type:#optional type ends up as Union, but we don't officially support Union
                    raise ValueError(type_error_message)
                if is_simple_type or arg_type_generic_parent_type==Literal:
                    nargs=None #exactly one
                    ultimate_type=arg_type
                else:
                    arg_type_subtypes=typing.get_args(arg_type)
                    if arg_type_generic_parent_type is list:
                        if not len(arg_type_subtypes)==1 \
                                or not (arg_type_subtypes[0] in supported_simple_types or typing.get_origin(arg_type_subtypes[0])==Literal):
                            raise ValueError(type_error_message)#ValueError(f"The method you are decorating has a parameter `{arg}` not filled by slack or the argparser you provided, and we can't automagically extend your argparser because the parameter's type hint is a list not annotated by a single subtype in: {','.join(supported_simple_types)}")
                        nargs="+"
                        ultimate_type=arg_type_subtypes[0]
                    elif arg_type_generic_parent_type is Union:
                        if not len(arg_type_subtypes)==2 or not type(None) in arg_type_subtypes:
                            raise ValueError(type_error_message)
                        subtype_of_optional=arg_type_subtypes[0] if arg_type_subtypes[1] is type(None) else arg_type_subtypes[1]
                        if subtype_of_optional in supported_simple_types or typing.get_origin(subtype_of_optional)==Literal:
                            nargs="?"
                            ultimate_type=subtype_of_optional
                        else:
                            double_subtypes=typing.get_args(subtype_of_optional)
                            if not typing.get_origin(subtype_of_optional) is list \
                                        or not len(double_subtypes)==1\
                                        or not (double_subtypes[0] in supported_simple_types or typing.get_origin(double_subtypes[0])==Literal):
                                raise ValueError(type_error_message)
                            nargs="*"
                            ultimate_type=double_subtypes[0]
                    else:
                        raise ValueError(type_error_message)
            if arg_default:#because otherwise the default won't actually work
                if nargs=="+":
                    nargs="*"
                elif nargs is None:
                    nargs="?"
            arg_type_str=format_arg_type(arg_type)
            
            add_argument_kwargs:dict[str,Any]=dict(nargs=nargs,default=arg_default,help=f'{arg_type_str}{f", default: {arg_default}" if arg_default else ""}')
            
            if not typing.get_origin(ultimate_type) == Literal:
                if ultimate_type is bool:
                    add_argument_kwargs["action"]=BoolAction
                else:
                    add_argument_kwargs["type"]=ultimate_type
            else:
                add_argument_kwargs["choices"]=typing.get_args(ultimate_type)            



            midfunc_argparser.add_argument(arg.name if not arg.kind==arg.KEYWORD_ONLY else f"--{arg.name}",**add_argument_kwargs)

        return midfunc_argparser

#adapted from https://stackoverflow.com/a/74272052/10773089
class BoolAction(Action):
    def __init__(
            self,
            option_strings,
            dest,
            nargs=None,
            default: bool = False,
            **kwargs,
    ):
        if nargs is not None and nargs != "?":
            raise ValueError('nargs not allowed')
        super().__init__(option_strings, dest, default=default, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if isinstance(values, str):
            values = values.lower()
        b = values in [True, 1, 'true', 'yes', '1', 'on']
        if not b and values not in [False, 0, 'false', 'no', '0', 'off']:
            raise ValueError('Invalid boolean value "%s".')
        setattr(namespace, self.dest, b)

def format_arg_type(arg_type):
    arg_type_str = str(arg_type)
    arg_type_str = arg_type_str.replace("typing.", "")
    arg_type_str = arg_type_str.replace("<class '", "")
    arg_type_str = arg_type_str.replace("'>", "")
    arg_type_str = arg_type_str.rstrip("]")
    arg_type_str = arg_type_str.replace("List[", "list of ")
    arg_type_str = arg_type_str.replace("list[", "list of ")
    arg_type_str = arg_type_str.replace("Literal[", "options: ")
    arg_type_str = arg_type_str.replace("Optional[", "(optional) ")
    return arg_type_str