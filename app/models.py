from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, RootModel, StrictStr, StringConstraints, model_validator, Extra


NonEmptyStr = Annotated[StrictStr, StringConstraints(min_length=1, strip_whitespace=True)]

# class ContributorRole(str, Enum):
#     TRANSLATOR = "translator"
#     REVISER = "reviser"
#     AUTHOR = "author"
#     SCHOLAR = "scholar"


class CopyrightStatus(str, Enum):
    UNKNOWN = "Unknown"
    COPYRIGHTED = "In copyright"
    PUBLIC_DOMAIN = "Public domain"


class LicenseType(str, Enum):
    # based on https://creativecommons.org/licenses/
    CC0 = "CC0"
    PUBLIC_DOMAIN_MARK = "Public Domain Mark"
    CC_BY = "CC BY"
    CC_BY_SA = "CC BY-SA"
    CC_BY_ND = "CC BY-ND"
    CC_BY_NC = "CC BY-NC"
    CC_BY_NC_SA = "CC BY-NC-SA"
    CC_BY_NC_ND = "CC BY-NC-ND"
    UNDER_COPYRIGHT = "under copyright"
    UNKNOWN = "unknown"


class OpenPechaModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class Copyright(OpenPechaModel):
    status: CopyrightStatus = CopyrightStatus.UNKNOWN
    notice: Optional[str] = ""
    info_url: Optional[str] = None



class LocalizedString(RootModel[dict[str, NonEmptyStr]]):
    root: dict[str, NonEmptyStr] = Field(min_length=1)

    def __getitem__(self, item: str) -> str:
        return self.root[item]


class PersonModelBase(OpenPechaModel):
    bdrc: str | None = None
    wiki: str | None = None
    name: LocalizedString
    alt_names: list[LocalizedString] | None = None


class PersonModelInput(PersonModelBase):
    pass


class PersonModelOutput(PersonModelBase):
    id: str


class SpanModel(OpenPechaModel):
    start: int = Field(..., ge=0, description="Start character position (inclusive)")
    end: int = Field(..., ge=1, description="End character position (exclusive)")

    @model_validator(mode="after")
    def validate_span_range(self):
        if self.start > self.end:
            raise ValueError("'start' must be less than 'end'")
        return self


class SegmentModel(OpenPechaModel):
    id: str
    span: SpanModel


class ExpressionModelBase(OpenPechaModel):
    title: LocalizedString
    alt_titles: list[LocalizedString] | None = None
    language: NonEmptyStr
    category: str | None = None 
    copyright: CopyrightStatus
    license: LicenseType

    @model_validator(mode="after")
    def validate_copyright_and_license(self):
        # Validate copyright enum
        if not isinstance(self.copyright, CopyrightStatus):
            valid_copyrights = [status.value for status in CopyrightStatus]
            raise ValueError(
                f"Invalid copyright value. Must be one of: {valid_copyrights}"
            )
        
        # Validate license enum
        if not isinstance(self.license, LicenseType):
            valid_licenses = [license.value for license in LicenseType]
            raise ValueError(
                f"Invalid license value. Must be one of: {valid_licenses}"
            )
        
        return self



class ExpressionModelOutputBase(OpenPechaModel):
    title: LocalizedString
    alt_titles: list[LocalizedString] | None = None
    language: NonEmptyStr
    category: str | None = None
    copyright: CopyrightStatus 
    license: LicenseType

    @model_validator(mode="after")
    def validate_copyright_and_license(self):
        # Validate copyright enum
        if not isinstance(self.copyright, CopyrightStatus):
            valid_copyrights = [status.value for status in CopyrightStatus]
            raise ValueError(
                f"Invalid copyright value. Must be one of: {valid_copyrights}"
            )
        
        # Validate license enum
        if not isinstance(self.license, LicenseType):
            valid_licenses = [license.value for license in LicenseType]
            raise ValueError(
                f"Invalid license value. Must be one of: {valid_licenses}"
            )
        
        return self


class ExpressionModelOutput(ExpressionModelOutputBase):
    id: str

class Segment(OpenPechaModel):
    segment_id: str
    content: str

class TextSegment(OpenPechaModel):
    search_segment_id: str
    content: str
    segments: list[Segment]

class AllTextSegments(OpenPechaModel):
    manifestation_id: str
    mapping: TextSegment
    metadata: ExpressionModelOutput