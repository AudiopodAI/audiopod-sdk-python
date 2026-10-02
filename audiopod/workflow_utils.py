from uuid import UUID


def canonical_uuid(value):
    return str(UUID(str(value)))


def uuid_fields(body):
    result = dict(body)
    for key in ("source_id", "project_id", "edition_id", "job_id", "template_id", "folder_id", "upload_session_id", "idempotency_key"):
        if result.get(key) is not None:
            result[key] = canonical_uuid(result[key])
    return result
