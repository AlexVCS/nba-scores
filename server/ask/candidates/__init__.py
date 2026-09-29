"""Ask candidate lookup (#200): bounded, typed candidates for the interpreter.

Use :class:`CandidateLookupService` (implements
``server.ask.protocols.CandidateLookup``). Aliases are loaded only through
:mod:`server.ask.candidates.aliases`, shared by every consumer.
"""
from server.ask.candidates.aliases import alias_version, get_alias_mapping
from server.ask.candidates.lookup import CandidateLookupService

__all__ = ["CandidateLookupService", "alias_version", "get_alias_mapping"]
