import json
from typing import Optional, Literal

from posthog.constants import PERSON_UUID_FILTER, SESSION_RECORDINGS_FILTER_IDS
from posthog.models.filters.mixins.common import BaseParamMixin
from posthog.models.filters.mixins.utils import cached_property
from posthog.models.property import Property


class Property:
    key: str
    operator: Optional[OperatorType]
    value: ValueT
    type: PropertyType


class PersonUUIDMixin(BaseParamMixin):
    @cached_property
    def person_uuid(self) -> Optional[str]:
        return self._data.get(PERSON_UUID_FILTER, None)


class SessionRecordingsMixin(BaseParamMixin):
    @cached_property
    def console_search_query(self) -> str | None:
        return self._data.get("console_search_query", None)

    @cached_property
    def console_logs(self) -> list[Literal["error", "warn", "info"]]:
        user_value = self._data.get("console_logs", None) or []
        if isinstance(user_value, str):
            user_value = json.loads(user_value)
        valid_values = [x for x in user_value if x in ["error", "warn", "info"]]
        return valid_values

    # @cached_property
    # def console_logs_filter(self) -> list[Literal["error", "warn", "info"]]:
    #     user_value = self._data.get("console_logs", None) or []
    #     if isinstance(user_value, str):
    #         user_value = json.loads(user_value)
    #     valid_values = [x for x in user_value if x in ["error", "warn", "info"]]
    #     return valid_values

    @cached_property
    def duration(self) -> Optional[list[Property]]:
        duration_filters_data_str = self._data.get("duration", None)
        if duration_filters_data_str:
            filter_data = json.loads(duration_filters_data_str)
            # TODO: Possibly not a Property
            return Property(**filter_data)
        return None

    @cached_property
    def session_ids(self) -> Optional[list[str]]:
        # Can be ['a', 'b'] or "['a', 'b']" or "a,b"
        session_ids_str = self._data.get(SESSION_RECORDINGS_FILTER_IDS, None)

        if session_ids_str is None:
            return None

        if isinstance(session_ids_str, list):
            recordings_ids = session_ids_str
        elif isinstance(session_ids_str, str):
            if session_ids_str.startswith("["):
                recordings_ids = json.loads(session_ids_str)
            else:
                recordings_ids = session_ids_str.split(",")

        if all(isinstance(recording_id, str) for recording_id in recordings_ids):
            # Sort for stable queries
            return sorted(recordings_ids)

        # If the property is at all present, we assume that the user wants to filter by it
        return []
