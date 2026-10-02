"""Provider-neutral public workflow types; runtime validation remains server-owned."""
from typing import Any, Dict, List, Literal, Optional, TypedDict

VOICE_CONSENT_VERSION = "2026-10-02.voice-consent.v1"


class PodcastTakeTiming(TypedDict):
    """Decoded WAV frame positions; both identity strings are SHA256 digests."""
    dialogue_id: str
    take_identity: Optional[str]
    audio_sha256: str
    format: Literal["wav"]
    start_frame: int
    end_frame: int
    sample_rate: int


class _PodcastDialogueDefaults(TypedDict, total=False):
    id: str
    take_identity: Optional[str]


class PodcastDialogue(_PodcastDialogueDefaults):
    """Typed projection; optional identity preserves legacy dialogue responses."""
    speaker: str
    text: str


class _PodcastProjectDefaults(TypedDict, total=False):
    dialogues: List[PodcastDialogue]
    combined_timing: Optional[List[PodcastTakeTiming]]


class PodcastProject(_PodcastProjectDefaults):
    """Typed take metadata projection; full SDK responses remain dictionaries."""
    id: str


DubbingOutput = Literal["audio", "srt", "vtt", "video"]
DubbingStatus = Literal["analyzing", "review_required", "generating", "export_partial", "settle_pending", "release_pending", "completed", "failed", "cancelled", "expired"]
ConsentProjectKind = Literal["account", "tts", "podcast", "dubbing"]
Readiness = TypedDict("Readiness", {"state": Literal["ready", "unavailable", "unknown"], "reason_code": Optional[str], "action": Optional[str]})
VoiceReadiness = TypedDict("VoiceReadiness", {"state": Literal["ready", "unavailable", "unknown"], "reason_code": str, "action": Literal["continue", "recheck", "choose_voice", "wait", "adjust_reference"]})
RationalDuration = TypedDict("RationalDuration", {"numerator": int, "denominator": int})
class _SettingsDefaults(TypedDict, total=False):
    audio_format: Literal["mp3", "wav"]
    speed: float
    delivery_mode: Literal["stable", "balanced", "creative"]
    background: Literal["none", "preserve"]
    background_gain_db: float

class DubbingSettings(_SettingsDefaults):
    catalog_voice_id: int

class _SegmentDefaults(TypedDict, total=False):
    speed: float
    delivery_mode: Literal["stable", "balanced", "creative"]

class DubbingSegment(_SegmentDefaults):
    id: str
    source_text: str
    target_text: str
    start_us: int
    end_us: int
    voice_id: int

class _ProjectDefaults(TypedDict, total=False):
    folder_id: Optional[str]

class CreateDubbingProject(_ProjectDefaults):
    source_id: str
    title: str
    source_language: str

class _EditionDefaults(TypedDict, total=False):
    required_outputs: List[DubbingOutput]

class CreateDubbingEdition(_EditionDefaults):
    target_language: str
    settings: DubbingSettings

SaveDubbingEdition = TypedDict("SaveDubbingEdition", {"expected_revision": int, "segments": List[DubbingSegment], "settings": DubbingSettings, "required_outputs": List[DubbingOutput]})
DubbingSource = TypedDict("DubbingSource", {"id": str, "filename": str, "source_duration": Optional[RationalDuration], "has_video": bool, "expires_at": Optional[str], "status": str, "media_url": Optional[str], "error_code": Optional[str]})
DubbingArtifact = TypedDict("DubbingArtifact", {"kind": str, "available": bool, "url": Optional[str], "expires_at": Optional[str], "classification": Literal["generated_original", "processed"]})
DubbingJob = TypedDict("DubbingJob", {"id": str, "edition_id": str, "revision": int, "status": DubbingStatus, "stage": str, "financial_disposition": Literal["held", "captured", "released"], "required_credits": int, "required_outputs": List[DubbingOutput], "artifacts": List[DubbingArtifact], "blockers": List[str], "warnings": List[Dict[str, Any]], "output_status": List[Dict[str, Any]], "error_code": Optional[str], "review_deadline": Optional[str], "export_deadline": Optional[str], "event_sequence": int})
DubbingEdition = TypedDict("DubbingEdition", {"id": str, "project_id": str, "target_language": str, "revision": int, "settings": DubbingSettings, "segments": List[DubbingSegment], "required_outputs": List[DubbingOutput], "owner_review_complete": bool, "latest_job": Optional[DubbingJob], "snapshot_stale": Dict[str, bool]})
DubbingProject = TypedDict("DubbingProject", {"id": str, "title": str, "source_id": str, "source": DubbingSource, "source_language": str, "folder_id": Optional[str], "created_at": str, "editions": List[DubbingEdition]})
DubbingQuote = TypedDict("DubbingQuote", {"edition_id": str, "revision": int, "action": Literal["analyze", "generate", "regenerate"], "quote_identity": str, "required_credits": int, "additional_credits": int, "billing_unit": Literal["account_credits"], "credits_per_source_second": int, "source_duration": RationalDuration, "required_outputs": List[DubbingOutput], "held_job_id": Optional[str], "review_deadline": Optional[str], "retranslate": bool})
class _ConfirmationDefaults(TypedDict, total=False):
    retranslate: bool

class DubbingConfirmation(_ConfirmationDefaults):
    edition_id: str
    expected_revision: int
    quote_identity: str
    idempotency_key: str

AnalyzeDubbing = TypedDict("AnalyzeDubbing", {"confirmations": List[DubbingConfirmation], "confirm": Literal[True]})
GenerateDubbing = TypedDict("GenerateDubbing", {"expected_revision": int, "quote_identity": str, "confirm": Literal[True]})
DubbingCapabilities = TypedDict("DubbingCapabilities", {"source_languages": List[str], "target_languages": List[str], "outputs": List[DubbingOutput], "audio_formats": List[str], "credits_per_source_second": int, "billing_unit": Literal["account_credits"], "readiness": Readiness})
class _GlossaryEntryDefaults(TypedDict, total=False):
    preferred_target: Optional[str]
    case_sensitive: bool

class GlossaryEntry(_GlossaryEntryDefaults):
    source: str
    mode: Literal["preferred", "keep_unchanged"]

class _GlossaryDefaults(TypedDict, total=False):
    entries: List[GlossaryEntry]

class GlossaryWrite(_GlossaryDefaults):
    expected_version: int
    mode: Literal["inherit", "override", "disable"]

DubbingGlossary = TypedDict("DubbingGlossary", {"language": str, "project_id": Optional[str], "version": int, "mode": str, "entries": List[GlossaryEntry]})
DubbingTemplate = TypedDict("DubbingTemplate", {"id": str, "label": str, "target_language": str, "settings": Dict[str, Any], "required_outputs": List[DubbingOutput], "voice_selection_required": bool})
ProjectFromTemplate = TypedDict("ProjectFromTemplate", {"template_id": str, "source_id": str, "title": str, "source_language": str, "settings": DubbingSettings, "target_language": str, "required_outputs": List[DubbingOutput]})
class _ReviewInvitationDefaults(TypedDict, total=False):
    invitation_token: str
    review_path: str

class DubbingReviewGrant(_ReviewInvitationDefaults):
    id: str
    edition_id: str
    recipient_email: str
    expires_at: str
    revoked: bool
    approved: bool
    approved_revision: Optional[int]
class _CommentRecipientDefaults(TypedDict, total=False):
    recipient_email: str

class DubbingComment(_CommentRecipientDefaults):
    id: str
    revision: int
    segment_id: str
    position_us: int
    body: str
    created_at: str
WriteDubbingComment = TypedDict("WriteDubbingComment", {"expected_revision": int, "segment_id": str, "position_us": int, "body": str})
DubbingReview = TypedDict("DubbingReview", {"grant_id": str, "expires_at": str, "project_title": str, "target_language": str, "revision": int, "state": Literal["ready", "waiting_for_revision"], "approved": bool, "segments": List[Dict[str, Any]], "artifacts": List[Dict[str, str]], "comments": List[DubbingComment]})
UploadLimits = TypedDict("UploadLimits", {"service": str, "plan": str, "max_upload_bytes": int, "max_duration_s": Optional[int], "multipart_threshold_bytes": int})
PresignUpload = TypedDict("PresignUpload", {"service": str, "filename": str, "content_type": str, "size_bytes": int})
PresignedUpload = TypedDict("PresignedUpload", {"upload_id": str, "url": str, "method": Literal["PUT"], "headers": Dict[str, str], "key_expires_in": int})
CropWindow = TypedDict("CropWindow", {"start_seconds": float, "end_seconds": float})
class _ConsentDefaults(TypedDict, total=False):
    project_kind: ConsentProjectKind
    project_id: Optional[str]
    source_id: Optional[str]
    reference_filename: Optional[str]
    recipient_email: Optional[str]
    allow_public_sharing: bool

class CreateVoiceConsent(_ConsentDefaults):
    recording_sha256: str
    window_sha256: str
    prepared_sha256: str
    crop: CropWindow
    consent_version: str
    confirm: bool

VoiceConsent = TypedDict("VoiceConsent", {"id": str, "state": Literal["awaiting_consent", "accepted", "revoked"], "consent_version": str, "consent_revision": int, "project_kind": ConsentProjectKind, "project_id": Optional[str], "source_id": Optional[str], "recording_sha256": str, "window_sha256": str, "prepared_sha256": str, "reference_filename": Optional[str], "reference_media": VoiceReadiness, "crop": CropWindow, "invitation_expires_at": str, "invitation_token": Optional[str], "allow_public_sharing": bool})
ReferenceDiagnostics = TypedDict("ReferenceDiagnostics", {"duration_seconds": float, "sample_rate": int, "silence_fraction": float, "clipping_fraction": float, "peak_dbfs": Optional[float], "rms_dbfs": Optional[float], "usable_windows": List[CropWindow], "warning_codes": List[str], "raw_sha256": str, "window_sha256": str, "prepared_sha256": Optional[str], "crop": CropWindow, "transcript_validation": VoiceReadiness})
VoiceReferenceAdmission = TypedDict("VoiceReferenceAdmission", {"admission_token": str, "expires_at": str, "consent_id": str, "consent_version": str, "consent_revision": int, "reference_revision": int, "recording_sha256": str, "reference": ReferenceDiagnostics, "transcript_validation": VoiceReadiness})
VoiceRegistration = TypedDict("VoiceRegistration", {"state": Literal["processing", "completed", "failed", "registration_uncertain", "cleanup_pending"], "voice_id": Optional[int], "voice_uuid": Optional[str], "display_name": Optional[str], "reference_revision": Optional[int], "readiness": VoiceReadiness, "error_code": Optional[str]})

class _PronunciationEntryDefaults(TypedDict, total=False):
    alias: str
    case_sensitive: bool
    mode: Literal["override", "disable"]

class PronunciationEntry(_PronunciationEntryDefaults):
    source: str

PronunciationPolicy = TypedDict("PronunciationPolicy", {"language": str, "project_kind": ConsentProjectKind, "project_id": Optional[str], "version": int, "mode": Literal["inherit", "override", "disable"], "entries": List[PronunciationEntry]})
ResolvedPronunciation = TypedDict("ResolvedPronunciation", {"language": str, "mode": str, "entries": List[PronunciationEntry], "versions": Dict[str,int], "identity": str})
PronunciationResolution = TypedDict("PronunciationResolution", {"snapshot": ResolvedPronunciation, "spoken_text": str, "changed": bool})
VoiceCapabilities = TypedDict("VoiceCapabilities", {"voice_id": int, "voice_revision": str, "operation": Literal["tts", "podcast", "audiobook", "multi_voice_tts", "audition"], "readiness": VoiceReadiness, "controls": List[str], "languages": List[str], "formats": List[str], "timing": Dict[str,VoiceReadiness], "resolved_identity": str})
ContextualAuditionQuote = TypedDict("ContextualAuditionQuote", {"billing_lane": str, "required_credits": Optional[int], "cost_cents": Optional[int], "quote_identity": str, "text_length": int, "voice_id": int, "voice_revision": str, "pronunciation_identity": str, "generation_params": Dict[str,Any], "spoken_text": str})
VoiceMetadata = TypedDict("VoiceMetadata", {"name": str, "description": str, "is_public": bool, "gender": str, "age_group": str, "use_case": str}, total=False)

DubbingFolder = TypedDict("DubbingFolder", {"id": str, "label": str, "kind": Literal["client", "series"]})
DubbingEvent = TypedDict("DubbingEvent", {"sequence": int, "state": str, "data": Dict[str, Any], "created_at": str})
DubbingProjectDeleted = TypedDict("DubbingProjectDeleted", {"project_id": str, "state": Literal["purge_pending"]})
