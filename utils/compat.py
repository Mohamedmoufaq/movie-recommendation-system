"""Tiny helpers: caching + secrets that also work when Streamlit is not installed
(so the data/recommender code can be tested from a plain terminal)."""
import os

try:
    import streamlit as st
    HAS_ST = True
except Exception:  # pragma: no cover
    st = None
    HAS_ST = False


def _passthrough(args, kwargs):
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]
    return lambda fn: fn


def cache_data(*args, **kwargs):
    """st.cache_data when Streamlit exists, otherwise a no-op decorator."""
    if HAS_ST:
        return st.cache_data(*args, **kwargs)
    return _passthrough(args, kwargs)


def cache_resource(*args, **kwargs):
    """st.cache_resource when Streamlit exists, otherwise a no-op decorator."""
    if HAS_ST:
        return st.cache_resource(*args, **kwargs)
    return _passthrough(args, kwargs)


def get_secret(name, default=None):
    """Read a secret from .streamlit/secrets.toml, else from an environment variable.
    Never crashes if the secret is missing."""
    if HAS_ST:
        try:
            value = st.secrets[name]
            if value:
                return str(value)
        except Exception:
            pass
    return os.environ.get(name, default)
