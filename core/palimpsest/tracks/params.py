"""Declarative parameter contract for analysis tracks — guard-rails G1 + G2.

A track declares its tunable behavior as a tuple of :class:`Param` instead of hand-rolling
``set_params`` / ``validate_params`` / ``parameters``. The :class:`ParameterizedTrack` mixin derives
the full contract the design principles require (see
``docs/development/design/analysis-design-principles.md`` §2) from that declaration:

  - **store-raw** on ``set_params`` (no coercion or clamping at set time);
  - **coerce + validate** at resolve time, raising :class:`ValueError` (→ HTTP 400) — including a
    clean 400 on a non-numeric value, instead of the uncaught 500 the per-track ``int(...)`` calls
    produced before (finding A5);
  - **reject unknown parameters** instead of silently ignoring them (finding A4);
  - one :meth:`ParameterizedTrack.resolved_params` that is the SOLE provenance source — the HTTP echo,
    the CLI ``pipeline_run.json``, and the on-disk run manifest all read it, so they can no longer
    disagree (finding A1).

**Acceptable-default rule (G2).** An *analytical* knob — one whose value changes the result for a
fixed input (seeds, iteration caps, df/feature thresholds, cluster/topic/state counts, similarity
cutoffs) — must be DECLARED and REPORTED. It may carry a default, but the default is never hidden: it
appears in ``resolved_params()`` and is written to disk. A ``locked`` param is reported with its fixed
value and rejects any attempt to set it (not user-tunable yet, but visible — ``locked`` is the
opposite of *hidden*, not of *default*). Only *structural* params (``kind="structural"``, one correct
value per document) may default silently.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, cast


class InsufficientCorpusError(ValueError):
    """The input is too small/degenerate for this analysis to run (e.g. fewer paragraphs than the
    minimum a topic model needs, or a corpus whose entire vocabulary is stop-words).

    Raised from ``extract`` instead of silently returning ``[]`` — a degenerate corpus must read as an
    honest failure with a reason, not as "ran fine, 0 annotations" (finding B5 / principle P5). It
    subclasses :class:`ValueError`, so the run handlers surface it through the same failed-job /
    skipped-track path as every other bad-input error, carrying its real message to the user."""


@dataclass(frozen=True)
class Param:
    """One declared parameter of an analysis track.

    ``type`` is a callable converter (``int``, ``float``, ``str``, or a custom one) applied to a
    user-supplied value; a conversion failure becomes a 400, never a 500. ``locked`` marks an
    analytical constant that is reported but not yet user-settable. ``kind`` records the
    acceptable-default classification (``"analytical"`` vs ``"structural"``) for the G2 rule.
    """

    name: str
    type: Callable[[Any], Any]
    required: bool = False
    default: Any = None
    choices: tuple[Any, ...] | None = None
    min: float | None = None
    max: float | None = None
    locked: bool = False
    kind: str = "analytical"
    help: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ("analytical", "structural"):
            raise ValueError(f"Param.kind must be 'analytical' or 'structural', got {self.kind!r}")
        # The G2 rule, enforced at declaration time: an analytical knob with a silent default that is
        # neither locked nor reported is exactly the banned "hidden default". Analytical params are
        # always reported by resolved_params(), so the only thing to forbid here is the contradiction
        # of a structural param being locked (locked implies an analytical constant a user might want).
        if self.kind == "structural" and self.locked:
            raise ValueError(f"structural param {self.name!r} cannot be locked")


def resolve_params(
    params: Sequence[Param],
    raw: dict[str, Any],
    *,
    reserved: Sequence[str] = ("force",),
    track: str = "",
) -> dict[str, Any]:
    """Resolve ``raw`` user input against the declared ``params``, raising ``ValueError`` (→ 400) on
    any unknown key, locked-param write, failed coercion, or out-of-range/invalid value.

    Returns the resolved {name: value} dict — the single source of truth for provenance. ``reserved``
    names (e.g. ``force``) are framework keys that are accepted and ignored, not track parameters.
    """
    declared = {p.name for p in params}
    reserved_set = set(reserved)
    unknown = [k for k in raw if k not in declared and k not in reserved_set]
    if unknown:
        valid = ", ".join(sorted(declared)) or "(none)"
        raise ValueError(
            f"unknown parameter(s) for {track or 'track'}: "
            + ", ".join(map(repr, sorted(unknown)))
            + f"; valid parameters are {valid}"
        )

    resolved: dict[str, Any] = {}
    for p in params:
        if p.name in raw:
            if p.locked:
                raise ValueError(
                    f"parameter {p.name!r} is locked to {p.default!r} and cannot be set"
                )
            try:
                value = p.type(raw[p.name])
            except (ValueError, TypeError) as e:
                tname = getattr(p.type, "__name__", str(p.type))
                # Surface the converter's own message (chained), not just the generic type name: a
                # converter like self_similarity's `_parse_inputs` raises a specific reason ("requires
                # 'chunk_label' …") that the user needs to see to fix the request.
                detail = f": {e}" if str(e) else ""
                raise ValueError(
                    f"parameter {p.name!r} must be {tname}, got {raw[p.name]!r}{detail}"
                ) from e
        else:
            if p.required:
                raise ValueError(f"parameter {p.name!r} is required")
            value = p.default

        if p.choices is not None and value not in p.choices:
            raise ValueError(
                f"parameter {p.name!r} must be one of "
                + ", ".join(map(repr, p.choices))
                + f"; got {value!r}"
            )
        if p.min is not None and value is not None and value < p.min:
            raise ValueError(f"parameter {p.name!r} must be >= {p.min}, got {value!r}")
        if p.max is not None and value is not None and value > p.max:
            raise ValueError(f"parameter {p.name!r} must be <= {p.max}, got {value!r}")
        resolved[p.name] = value
    return resolved


def _strip_prefix(key: str, prefix: str) -> str:
    return key[len(prefix):] if key.startswith(prefix) else key


def track_provenance(extractor: Any) -> dict[str, Any]:
    """Best-effort *effective* parameters of a track, normalized to bare keys, for the on-disk run
    record (G3/C1).

    Prefers ``effective_params()`` (the post-run truth on a :class:`ParameterizedTrack`: resolved
    request with any runtime clamp applied), then ``resolved_params()``, ``validate_params()``
    (self_similarity's specialized validator), then ``parameters()`` (every extractor has it).
    Whatever the source returns is normalized by stripping any ``"{track}."`` namespace prefix, so the
    record reads the same regardless of which entry point or track produced it. For any param the
    track clamped at runtime (effective ≠ request — the *record-effective* policy, §2.3), the reported
    value is the EFFECTIVE one and an extra ``{name}_requested`` key records what was asked, so disk
    never lies and the clamp is never silent. Called after a run has succeeded, so the validators here
    will not raise."""
    name = getattr(extractor, "name", "")
    prefix = f"{name}."
    raw: dict[str, Any] = {}
    for attr in ("effective_params", "resolved_params", "validate_params", "parameters"):
        fn = getattr(extractor, attr, None)
        if callable(fn):
            raw = cast("dict[str, Any]", fn())
            break
    bare = {_strip_prefix(k, prefix): v for k, v in raw.items()}

    clamp_fn = getattr(extractor, "clamped_params", None)
    if callable(clamp_fn):
        for k, requested in cast("dict[str, Any]", clamp_fn()).items():
            bare[f"{_strip_prefix(k, prefix)}_requested"] = requested
    return bare


def track_clamps(extractor: Any) -> list[str]:
    """Bare names of the params a track clamped at runtime (effective ≠ request), for the provenance
    record's top-level ``clamped`` flag. Empty for tracks that did not clamp or are not parameterized."""
    fn = getattr(extractor, "clamped_params", None)
    if not callable(fn):
        return []
    name = getattr(extractor, "name", "")
    prefix = f"{name}."
    return sorted(_strip_prefix(k, prefix) for k in cast("dict[str, Any]", fn()))


class ParameterizedTrack:
    """Mixin giving a track the declarative parameter contract.

    Subclasses set ``PARAMS`` (a tuple of :class:`Param`) and read resolved values via
    :meth:`param` / :meth:`resolved_params` inside ``extract``. They must call ``super().__init__()``.
    """

    PARAMS: tuple[Param, ...] = ()
    RESERVED_PARAMS: tuple[str, ...] = ("force",)

    def __init__(self) -> None:
        self._raw_params: dict[str, Any] = {}
        # Runtime-effective overrides for params clamped to input feasibility during extract (e.g.
        # n_topics reduced to the corpus size). Empty unless a track calls record_effective(), so the
        # whole effective/clamp machinery is invisible for tracks that never clamp.
        self._effective_params: dict[str, Any] = {}

    @property
    def name(self) -> str:  # pragma: no cover - each track overrides this
        raise NotImplementedError

    def set_params(self, params: dict[str, Any]) -> None:
        """Store user-supplied params verbatim (no coercion/clamp here — that happens at resolve)."""
        self._raw_params.update(params)

    def resolved_params(self) -> dict[str, Any]:
        """The validated, resolved parameter values — what the user *asked* for. Raises on bad input."""
        return resolve_params(
            self.PARAMS, self._raw_params, reserved=self.RESERVED_PARAMS, track=self.name
        )

    def validate_params(self) -> dict[str, Any]:
        """Validate and echo the resolved params (→ HTTP 400 on any error)."""
        return self.resolved_params()

    def record_effective(self, name: str, value: Any) -> None:
        """Record the runtime-EFFECTIVE value of a declared param when the track clamped it to input
        feasibility (the *record-effective* policy, §2.3). The effective value — not the request — is
        what :meth:`effective_params` / provenance / the signal manifest report, so disk never lies and
        a clamp is never silent. ``name`` must be a declared param."""
        if name not in {p.name for p in self.PARAMS}:
            raise KeyError(f"{name!r} is not a declared parameter of {self.name}")
        self._effective_params[name] = value

    def effective_params(self) -> dict[str, Any]:
        """Resolved params with any recorded runtime-effective overrides applied — the post-run
        provenance source. Identical to :meth:`resolved_params` unless the track clamped a value."""
        resolved = self.resolved_params()
        resolved.update(self._effective_params)
        return resolved

    def clamped_params(self) -> dict[str, Any]:
        """``{name: requested_value}`` for each param whose effective runtime value differs from the
        request — drives the ``{name}_requested`` provenance keys and the ``clamped`` flag."""
        resolved = self.resolved_params()
        return {
            name: resolved[name]
            for name, eff in self._effective_params.items()
            if name in resolved and resolved[name] != eff
        }

    def param(self, name: str) -> Any:
        """Resolved value of a single declared parameter (validates the whole set)."""
        return self.resolved_params()[name]

    def parameters(self) -> dict[str, Any]:
        """Namespaced provenance view for ``pipeline_run.json`` (``{track.param: value}``), reporting
        the EFFECTIVE values so the aggregate provenance agrees with the per-track run record."""
        return {f"{self.name}.{k}": v for k, v in self.effective_params().items()}
