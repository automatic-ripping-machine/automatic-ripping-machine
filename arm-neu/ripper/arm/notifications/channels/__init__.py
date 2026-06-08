"""Channel-specific senders. Each module exports a ``send_<type>``
function with the signature ``(...) -> tuple[bool, str | None]`` where
the str is None on success and a short error message on failure."""
