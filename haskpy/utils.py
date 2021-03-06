import functools
import inspect
import attr
import hypothesis.strategies as st


def immutable(maybe_cls=None, eq=False, repr=False, **kwargs):
    return attr.s(
        maybe_cls=maybe_cls,
        frozen=True,
        eq=eq,
        order=False,
        hash=False,
        str=False,
        repr=repr,
        **kwargs
    )


def singleton(C):
    return C()


class decorator():
    """Base class for various decorators"""

    def __init__(self, f):
        self.f = f
        self.__doc__ = f.__doc__
        self.__name__ = f.__name__
        return


class class_function(decorator):
    """Class method that isn't a method of the instances"""

    def __get__(self, obj, cls):
        if obj is None:
            return self.f.__get__(cls, type(cls))
        else:
            raise AttributeError(
                "'{0}' object has no attribute '{1}'".format(
                    cls.__name__,
                    self.f.__name__,
                )
            )


class class_property(decorator):
    """Class attribute that isn't an attribute of the instances

    To access the docstring, use ``__dict__`` as
    ``SomeClass.__dict__["some_attribute"].__doc__``

    """

    def __get__(self, obj, cls):
        if obj is None:
            return self.f.__get__(obj, cls)(cls)
        else:
            raise AttributeError(
                "'{0}' object has no attribute '{1}'".format(
                    cls.__name__,
                    self.f.__name__,
                )
            )


class abstract_function(decorator):
    """Function that has no implementation yet"""

    def __call__(self, *args, **kwargs):
        raise NotImplementedError(
            "'{0}' function is abstract".format(self.f.__name__)
        )

    def __get__(self, obj, cls):
        return abstract_function(self.f.__get__(obj, cls))


class abstract_property(decorator):
    """Property that has no implementation yet

    To access the property ``abstract_property`` object without raising
    ``NotImplementedError``, use ``__dict__``. For instance, to access the
    docstring:

    .. code-block:: python

        class Foo():

            @abstract_property
            def bar(self):
                '''My docstring'''

        Foo.__dict__["bar"].__doc__
        isinstance(Foo.__dict__["bar"], abstract_property)

    """

    def __get__(self, obj, cls):
        self.f.__get__(obj, cls)
        raise NotImplementedError(
            "'{0}' attribute of type object '{1}' is abstract".format(
                self.f.__name__,
                cls.__name__,
            )
            if obj is None else
            "'{0}' attribute of object '{1}' is abstract".format(
                self.f.__name__,
                cls.__name__,
            )
        )


def abstract_class_property(f):
    return abstract_property(class_function(f))


def abstract_class_function(f):
    return abstract_function(class_function(f))


@immutable
class nonexisting_function():
    """Mark method non-existing

    This is a workaround for Python forcefully creating some methods. One
    cannot create objects that don't have ``__eq__``, ``__ge__``, ``__gt__``
    and many other methods. They are there and it's not possible to delete
    them. With this wrapper you can override those methods so that they won't
    show up in ``__dir__`` listing and if accessed in any way,
    ``AttributeError`` is raised. Note that it just hides the methods, one can
    still access them as ``object.__getattribute__(obj, "__eq__")``.

    """

    method = attr.ib()
    cls = attr.ib(default=None)

    def __call__(self, *args, **kwargs):
        name = self.method.__name__
        # The method doesn't exist
        raise TypeError(
            "No {0} function".format(name)
            if self.cls is None else
            "Class {0} has no {1} method".format(self.cls.__name__, name)
        )

    def __get__(self, obj, objtype):
        # Bind the method to a class
        return nonexisting_function(self.method, cls=objtype)


def update_argspec(spec, args, kwargs):

    # TODO: Instead of running getfullargspec after every partial evaluation,
    # it might be faster to use the existing argspec and update that based on
    # args and kwargs. However, the speed gains might be quite small and one
    # needs to be very careful to implement exactly the same logic that Python
    # itself uses. It is possible that this logic changes from one Python
    # version to another, so it might become a maintenance nightmare. Still,
    # perhaps worth at least checking.
    #
    # Below is just some sketching.

    no_varargs = spec.varargs is None

    nargs_takes = len(spec.args)
    nargs_given = len(args)
    nargs_remain = nargs_takes - nargs_given
    if no_varargs and nargs_remain < 0:
        raise TypeError(
            "function takes {takes} positional argument but {given} were given"
            .format(
                name=name,
                takes=nargs_takes,
                given=nargs_given,
            )
        )

    new_args = spec.args[nargs_given:]
    new_defaults = spec.defaults[-nargs_remain:] if nargs_remain > 0 else None

    # FIXME:
    new_kwonlyargs = spec.kwonlyargs
    new_kwonlydefaults = spec.kwonlydefaults

    return inspect.FullArgSpec(
        args=new_args,
        varargs=spec.varargs,
        varkw=spec.varkw,
        defaults=new_defaults,
        kwonlyargs=new_kwonlyargs,
        kwonlydefaults=new_kwonlydefaults,
        # FIXME: What to do with this?
        annotations=spec.annotations,
    )
    pass


def count_required_arguments(argspec):

    # Positional arguments without defaults provided
    n_args = len(argspec.args) - (
        0 if argspec.defaults is None else
        len(argspec.defaults)
    )

    # Positional required arguments may get into required keyword
    # argument position if some positional arguments before them are
    # given as keyword arguments. For instance:
    #
    #   curry(lambda x, y: x - y)(x=5)
    #
    # Now, y becomes a keyword argument but it's still required as it
    # doesn't have any default value. Handle this by looking at
    # kwonlyargs that don't have a value in kwonlydefaults.
    defaults = (
        set() if argspec.kwonlydefaults is None else
        set(argspec.kwonlydefaults.keys())
    )
    kws = set(argspec.kwonlyargs)
    n_kw = len(kws.difference(defaults))

    return n_args + n_kw


@immutable
class Wrapped():


    """Original function that provides metainformation"""
    __unwrapped = attr.ib()


    """Wrapped function that is actually called"""
    __wrapped = attr.ib()


    def __call__(self, *args, **kwargs):
        return self.__wrapped(*args, **kwargs)


    def __repr__(self):
        return repr(self.__wrapped)


    @property
    def __module__(self):
        return self.__unwrapped.__module__


    @property
    def __signature__(self):
        return inspect.signature(self.__unwrapped)


    @property
    def __doc__(self):
        return self.__unwrapped.__doc__


def wraps(f):
    """Simple wrapping function similar to functools.wraps

    Aims to be a bit simpler and faster, but not sure about it. Experimenting
    at the moment.

    """
    def wrap(g):
        return Wrapped(f, g)
    return wrap




def curry(f, wrap=True):
    # toolz Python package has curry function but it's unusable. The main
    # problem being you don't get errors when doing something wrong but instead
    # some really weird results.
    #
    # For instance, when a type error is raised nested inside the function, it
    # will be silenced: https://github.com/pytoolz/toolz/issues/471. That is,
    # the following doesn't raise an exception but returns a weird function:
    #
    # >>> toolz.curry(lambda *args, **kwargs: (lambda x, y: x - y)(*args, **kwargs))(5, 3, 1)
    #
    # In HaskPy, this resulted in the following example to not raise an error
    # but give weird results:
    #
    # >>> haskpy.compose(pyhask.map, pyhask.map)(
    # ...     lambda x: 100*x,
    # ...     haskpy.Just(pyhask.List(1,2,3)),
    # ...     "these extra arguments",
    # ...     "should cause an error"
    # ... )
    #
    # Also, this should raise an error:
    #
    # >>>  toolz.curry(lambda *args, **kwargs: (lambda x, y: x + y)(*args, **kwargs))(1, "h")
    #
    # In Haskpy, this corresponds to a missing error from:
    #
    # >>> haskpy.Just(pyhask.List(1,2,3)).map(lambda x: x+1)
    #
    # Also, toolz.curry seems overly complex and bloated. I have no idea what
    # they are actually doing with all that code and magic.. At least for my
    # purposes, currying is very simple as the implementation below shows.
    #
    # So, let's implement our own simple curry function correctly.

    if not callable(f):
        raise TypeError("'{}' object is not callable".format(type(f).__name__))

    def wrapped(*args, **kwargs):

        try:
            # Handle a normal fully evaluated function fast. We want to get
            # full argspec only if necessary as that takes quite a bit of time
            # compared to just evaluating a function.
            return f(*args, **kwargs)
        except TypeError:
            fp = functools.partial(f, *args, **kwargs)
            try:
                # This is quite slow.. It's about 1000x slower than just
                # normally calling a function. See:
                # https://bugs.python.org/issue37010. Any way to speed it up,
                # do something else or avoid it?
                #
                # TODO: Perhaps worth considering if it would speed things up
                # if the full argspec is propagated recursively to curry for
                # partially evaluated functions. That way, they can just update
                # the existing argspec based on args and kwargs instead of
                # finding it from scratch. See update_argspec above. Then,
                # curry function would take argspec as an optional argument.
                spec = inspect.getfullargspec(fp)
            except TypeError:
                # This exception is raised when invalid arguments (positional
                # or keyword) are passed. To make the exception traceback
                # simpler, raise the original TypeError. Also, raise it outside
                # this try-except so these exceptions won't show up in the
                # traceback.
                pass
            else:
                # The original function raised TypeError but there's
                # nothing wrong in how the call signature was used. There
                # are now two possibilities:
                #
                # 1. The function is still waiting for some required inputs.
                #    In that case, don't raise the error, just partially
                #    evaluate the function (and curry it).
                if count_required_arguments(spec) > 0:
                    return curry(fp, wrap=wrap)
                # 2. The function received all required arguments, thus the
                #    error must have happened somewhere inside the
                #    function. In that case, just raise the original error.

            # The function either got invalid arguments or raised TypeError
            # somewhere inside its computations. Just raise that error.
            raise

    # NOTE: functools.wraps is a bit slow. Thus, currying functions all the
    # time might be a bit slow. Without wrapping, curry takes about 0.3
    # microseconds. With functools.wraps, 3 microseconds. With my own simple
    # wraps method, it takes 1 microsecond. Let's use that for now. Not sure if
    # it misses something. If so, use functools.wraps.

    return wraps(f)(wrapped) if wrap else wrapped


def curry_new(f, argspec=None):
    """Experimental fast curry that updates argspec"""

    if not callable(f):
        raise TypeError("'{}' object is not callable".format(type(f).__name__))

    # NOTE: functools.wraps is a bit slow. Thus, currying functions all the
    # time might be a bit slow. Without wrapping, curry takes about 0.3
    # microseconds. With functools.wraps, 3 microseconds. With my own simple
    # wraps method, it takes 1 microsecond. Let's use that for now. Not sure if
    # it misses something. If so, use functools.wraps.

    @wraps(f)
    def wrapped(*args, **kwargs):
        nonlocal argspec

        try:
            # Handle a normal fully evaluated function fast. We want to get
            # full argspec only if necessary as that takes quite a bit of time
            # compared to just evaluating a function.
            return f(*args, **kwargs)
        except TypeError:
            if argspec is None:
                argspec = inspect.getfullargspec(f)
            try:
                new_argspec = update_argspec("foo", argspec, args, kwargs)
            except TypeError:
                # This exception is raised when invalid arguments (positional
                # or keyword) are passed. To make the exception traceback
                # simpler, raise the original TypeError. Also, raise it outside
                # this try-except so these exceptions won't show up in the
                # traceback.
                pass
            else:
                # The original function raised TypeError but there's
                # nothing wrong in how the call signature was used. There
                # are now two possibilities:
                #
                # 1. The function is still waiting for some required inputs.
                #    In that case, don't raise the error, just partially
                #    evaluate the function (and curry it).
                if count_required_arguments(new_argspec) > 0:
                    return curry_new(
                        functools.partial(f, *args, **kwargs),
                        argspec=new_argspec
                    )
                # 2. The function received all required arguments, thus the
                #    error must have happened somewhere inside the
                #    function. In that case, just raise the original error.
                pass

            # The function either got invalid arguments or raised TypeError
            # somewhere inside its computations. Just raise that error.
            raise

    return wrapped


def identity(x):
    """a -> a"""
    return x


class PerformanceWarning(Warning):
    pass


@st.composite
def draw_args(draw, f, *args):
    return f(*(draw(a) for a in args))


@st.composite
def sample_type(draw, types, types1=[], types2=[]):
    if len(types) == 0:
        raise ValueError("Must provide at least one concrete type")
    arg = st.deferred(lambda: sample_type(types, types1, types2))
    return draw(
        st.one_of(
            # Concrete types
            *[st.just(t) for t in types],
            # One-argument type constructors
            *[
                draw_args(t1, arg)
                for t1 in types1
            ],
            # Two-argument type constructors
            *[
                draw_args(t2, arg, arg)
                for t2 in types2
            ],
        )
    )


def sample_sized(e, size=None):
    return (
        e if size is None else
        st.tuples(*(size * [e]))
    )


def eq_test(x, y, data, **kwargs):
    try:
        # Prefer __eq_test__ because it propagates data correctly. If it's not
        # available, x and y are probably either built-in types or some other
        # simple types which are always instances of Eq.
        eq = x.__eq_test__
    except AttributeError:
        return x == y
    else:
        return eq(y, data, **kwargs)


def assert_output(f):
    """Assert that the output pair elements are equal"""

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        xs = f(*args)
        x0 = xs[0]
        for xi in xs[1:]:
            assert eq_test(x0, xi, **kwargs)
        return

    return wrapped
