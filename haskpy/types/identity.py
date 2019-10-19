import attr

from haskpy.typeclasses import Monad
from .compose import Compose


@attr.s(frozen=True, repr=False)
class Identity(Monad):


    x = attr.ib()


    @classmethod
    def pure(cls, x):
        return cls(x)


    def bind(self, f):
        """Identity a -> (a -> Identity b) -> Identity b"""
        return f(self.x)


    def __repr__(self):
        return "Identity({})".format(repr(self.x))


def IdentityT(X):

    IdentityX = Compose(X, Identity)

    @attr.s(frozen=True, repr=False)
    class Transformed(IdentityX, Monad):


        def bind(self, f):
            """IdentityT m a -> (a -> IdentityT m b) -> IdentityT m b

            In decomposed form, this is:

              m (Identity a) -> (a -> m (Identity b)) -> m (Identity b)

            Let's write the types of the relevant pieces:

              self :: IdentityT m a

              f :: a -> IdentityT m b

              decompose(self) :: m (Identity a)

              g :: Identity a -> m (Identity b)
              g = lambda ia: f(ia.x).decomposed

              y :: m (Identity b)
              y = decompose(self).bind(g)

              Transformed(y) :: IdentityT m b


            """
            # mia :: m (Identity a)
            mia = self.decomposed

            # g :: Identity a -> m (Identity b)
            g = lambda ia: f(ia.x).decomposed

            # y :: m (Identity b)
            y = self.decomposed.bind(g)

            return Transformed(y) # :: IdentityT m b


        def __repr__(self):
            return "IdentityT({0})({1})".format(X.__name__, repr(self.decomposed))


    return Transformed
