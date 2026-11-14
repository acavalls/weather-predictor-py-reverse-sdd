"""ML domain events.

The ML bounded context is stateless — predictions are computed, not persisted.
Domain events are not needed for this context.

Events will be generated at the application layer (use case handlers)
when predictions are requested or models are trained.
"""
