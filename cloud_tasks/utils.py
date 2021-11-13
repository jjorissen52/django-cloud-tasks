"""
Copyright (c) 2019 JP Jorissen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import inspect

from django.urls.base import reverse

from cloud_tasks import conf


def get_default_args(func):
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }


def named_method_params(method, args, kwargs):
    """
    Takes a method and its arguments and returns a dictionary of all values that will be passed to it. This allows for
    easy inspection.
    """
    args_names = method.__code__.co_varnames[:method.__code__.co_argcount]
    params = get_default_args(method)
    args_dict = {**dict(zip(args_names, args)), **kwargs}
    params.update(args_dict)
    return params


def hardcode_reverse(view_name, args=None, kwargs=None):
    return f'{conf.ROOT_URL}{reverse(view_name, args=args, kwargs=kwargs)}'
