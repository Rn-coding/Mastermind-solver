"""Code setter modules for Mastermind."""

from mastermind.setters.base import BaseSetter
from mastermind.setters.fixed import KnownFixedSetter, RandomFixedSetter

__all__ = ["BaseSetter", "KnownFixedSetter", "RandomFixedSetter"]
