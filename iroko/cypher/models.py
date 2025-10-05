from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum


class IdentifierType(str, Enum):
    ARK = "ark"
    ARXIV = "arxiv"
    DOI = "doi"
    BIBCODE = "bibcode"
    EAN8 = "ean8"
    EAN13 = "ean13"
    HANDLE = "handle"
    ISBN = "isbn"
    ISSN = "issn"
    ISSN_L = "issn_l"
    ISSN_P = "issn_p"
    ISSN_E = "issn_e"
    ISSN_C = "issn_c"
    ISSN_O = "issn_o"
    ISTC = "istc"
    LSID = "lsid"
    PMID = "pmid"
    PMCID = "pmcid"
    PURL = "purl"
    UPC = "upc"
    URL = "url"
    URN = "urn"
    ORCID = "orcid"
    GND = "gnd"
    ADS = "ads"
    OAI = "oai"
    PRNPS = "prnps"
    ERNPS = "ernps"
    OAIURL = "oaiurl"
    SRCID = "srcid"
    EISSN = "eissn"
    LISSN = "lissn",
    PISSN = "pissn"
    IROUID = "irouid"
    GRID = "grid"
    WKDATA = "wkdata"
    ROR = "ror"
    ISNI = "isni"
    ORGREF = "orgref"
    FUDREF = "fudref"
    REUP = "reup"
    ORGAID = "orgaid"
    UNIID = "uniid"
    ORGID = "orgid"
    WOS = "wos"

## Sources

class SourceType(str, Enum):
    JOURNAL = "JOURNAL"
    SERIAL = "SERIAL"
    STUDENT = "STUDENT"
    POPULARIZATION = "POPULARIZATION"
    REPOSITORY = "REPOSITORY"
    WEBSITE = "WEBSITE"
    OTHER = "OTHER"


class SourceStatus(str, Enum):
    APPROVED = "APPROVED"
    TO_REVIEW = "TO_REVIEW"
    UNOFFICIAL = "UNOFFICIAL"


class RepositoryStatus(str, Enum):
    DELETED = "DELETED"
    ERROR = "ERROR"
    FETCHING = "FETCHING"
    IDENTIFIED = "IDENTIFIED"
    HARVESTED = "HARVESTED"
    RECORDED = "RECORDED"
    ENRICHED = "ENRICHED"


class Identifier(BaseModel):
    idtype: str
    value: str


class ISSN(BaseModel):
    p: Optional[str] = None
    e: Optional[str] = None
    l: Optional[str] = None


class RNPS(BaseModel):
    p: Optional[str] = None
    e: Optional[str] = None


class SaveInfo(BaseModel):
    user_id: Optional[str] = None
    comment: Optional[str] = None
    updated: Optional[datetime] = None


class OrganizationRelation(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None


class ClassificationTerm(BaseModel):
    id: Optional[str] = None
    description: Optional[str] = None
    vocabulary: Optional[str] = None


class Source(BaseModel):
    id: str
    identifiers: List[Identifier]
    title: str
    source_status: SourceStatus
    source_type: SourceType
    name: Optional[str] = None
    aliases: Optional[List[str]] = None
    repository_status: Optional[RepositoryStatus] = None
    source_system: Optional[str] = None
    description: Optional[str] = None
    url: Optional[List[str]] = None
    email: Optional[str] = None
    logo: Optional[str] = None
    seriadas_cubanas: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    subtitle: Optional[str] = None
    shortname: Optional[str] = None
    purpose: Optional[str] = None
    frequency: Optional[str] = None
    issn: Optional[ISSN] = None
    rnps: Optional[RNPS] = None
    _save_info: Optional[SaveInfo] = None
    _save_info_updated: Optional[datetime] = None
    organizations: Optional[List[OrganizationRelation]] = None
    classifications: Optional[List[ClassificationTerm]] = None

    class Config:
        extra = "allow"


## Projects

class TitleType(str, Enum):
    ALTERNATIVE_TITLE = "AlternativeTitle"
    SUBTITLE = "Subtitle"
    TRANSLATED_TITLE = "TranslatedTitle"
    OTHER = "Other"


class NameType(str, Enum):
    ORGANIZATIONAL = "Organizational"
    PERSONAL = "Personal"


class ContributorType(str, Enum):
    CONTACT_PERSON = "ContactPerson"
    DATA_COLLECTOR = "DataCollector"
    DATA_CURATOR = "DataCurator"
    DATA_MANAGER = "DataManager"
    DISTRIBUTOR = "Distributor"
    EDITOR = "Editor"
    HOSTING_INSTITUTION = "HostingInstitution"
    PRODUCER = "Producer"
    PROJECT_LEADER = "ProjectLeader"
    PROJECT_MANAGER = "ProjectManager"
    PROJECT_MEMBER = "ProjectMember"
    REGISTRATION_AGENCY = "RegistrationAgency"
    REGISTRATION_AUTHORITY = "RegistrationAuthority"
    RELATED_PERSON = "RelatedPerson"
    RESEARCHER = "Researcher"
    RESEARCH_GROUP = "ResearchGroup"
    RIGHTS_HOLDER = "RightsHolder"
    SPONSOR = "Sponsor"
    SUPERVISOR = "Supervisor"
    WORK_PACKAGE_LEADER = "WorkPackageLeader"
    OTHER = "Other"


class FundType(str, Enum):
    ISNI = "ISNI"
    GRID = "GRID"
    CROSSREF_FUNDER = "Crossref Funder"


class RelationType(str, Enum):
    IS_CITED_BY = "isCitedBy"
    CITES = "Cites"
    IS_SUPPLEMENT_TO = "IsSupplementTo"
    IS_SUPPLEMENTED_BY = "IsSupplementedBy"
    IS_CONTINUED_BY = "IsContinuedBy"
    CONTINUES = "Continues"
    IS_DESCRIBED_BY = "IsDescribedBy"
    DESCRIBES = "Describes"
    HAS_METADATA = "HasMetadata"
    IS_METADATA_FOR = "IsMetadataFor"
    HAS_VERSION = "HasVersion"
    IS_VERSION_OF = "IsVersionOf"
    IS_NEW_VERSION_OF = "IsNewVersionOf"
    IS_PREVIOUS_VERSION_OF = "IsPreviousVersionOf"
    IS_PART_OF = "IsPartOf"
    HAS_PART = "HasPart"
    IS_REFERENCED_BY = "IsReferencedBy"
    REFERENCES = "References"
    IS_DOCUMENTED_BY = "IsDocumentedBy"
    DOCUMENTS = "Documents"
    IS_COMPILED_BY = "IsCompiledBy"
    COMPILES = "Compiles"
    IS_VARIANT_FORM_OF = "IsVariantFormOf"
    IS_ORIGINAL_FORM_OF = "IsOriginalFormOf"
    IS_IDENTICAL_TO = "IsIdenticalTo"
    IS_REVIEWED_BY = "IsReviewedBy"
    REVIEWS = "Reviews"
    IS_DERIVED_FROM = "IsDerivedFrom"
    IS_SOURCE_OF = "IsSourceOf "
    IS_REQUIRED_BY = "IsRequiredBy"
    REQUIRES = "Requires"


class ResourceTypeGeneral(str, Enum):
    AUDIOVISUAL = "Audiovisual"
    COLLECTION = "Collection"
    DATA_PAPER = "DataPaper"
    DATASET = "Dataset"
    EVENT = "Event"
    IMAGE = "Image"
    INTERACTIVE_RESOURCE = "InteractiveResource"
    MODEL = "Model"
    PHYSICAL_OBJECT = "PhysicalObject"
    SERVICE = "Service"
    SOFTWARE = "Software"
    SOUND = "Sound"
    TEXT = "Text"
    WORKFLOW = "Workflow"
    OTHER = "Other"


class DateType(str, Enum):
    ACCEPTED = "Accepted"
    AVAILABLE = "Available"
    ISSUED = "Issued"


class ProjectTitle(BaseModel):
    title: str
    lang: Optional[str] = None
    titleType: Optional[TitleType] = None


class Affiliation(BaseModel):
    id: Optional[str] = None
    identifiers: Optional[List[AffiliationIdentifier]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    label: Optional[str] = None
    roles: Optional[List[str]] = None


class Creator(BaseModel):
    creatorName: str
    nameType: Optional[NameType] = None
    givenName: str
    familyName: str
    id: Optional[str] = None
    identifiers: Optional[List[CreatorIdentifier]] = None
    affiliations: Optional[List[Affiliation]] = None


class ContributorIdentifier(BaseModel):
    idtype: str
    value: str


class Contributor(BaseModel):
    contributorType: Optional[ContributorType] = None
    contributorName: Optional[str] = None
    nameType: Optional[NameType] = None
    givenName: Optional[str] = None
    familyName: Optional[str] = None
    id: Optional[str] = None
    identifiers: Optional[List[ContributorIdentifier]] = None
    affiliations: Optional[List[Affiliation]] = None


class FundingReference(BaseModel):
    founderName: Optional[str] = None
    funderIdentifier: Optional[FunderIdentifier] = None
    fundingStream: Optional[str] = None
    awardNumber: Optional[str] = None
    awardURI: Optional[str] = None
    awardTitle: Optional[str] = None


class RelatedIdentifier(BaseModel):
    idValue: str
    idType: IdentifierType
    relationType: RelationType
    relatedMetadataScheme: Optional[str] = None
    schemeURI: Optional[str] = None
    schemeType: Optional[str] = None
    resourceTypeGeneral: Optional[ResourceTypeGeneral] = None


class DateRight(BaseModel):
    dateValue: str
    dateType: DateType


class PublishDate(BaseModel):
    dateValue: str
    dateType: DateType


class Project(BaseModel):
    id: str
    identifiers: List[Identifier]
    title: List[ProjectTitle]
    creator: List[Creator]
    contributor: Optional[List[Contributor]] = None
    fundingReference: Optional[List[FundingReference]] = None
    alternateIdentifier: Optional[List[Identifier]] = None
    relatedIdentifier: Optional[List[RelatedIdentifier]] = None
    datesRights: Optional[List[DateRight]] = None
    language: Optional[List[str]] = None
    publisher: Optional[List[str]] = None
    publishDate: Optional[PublishDate] = None

    class Config:
        extra = "allow"


## Organization

class OrgStatus(str, Enum):
    ACTIVE = "active"
    OBSOLETE = "obsolete"
    REDIRECTED = "redirected"
    UNKNOWN = "unknown"


class OrgType(str, Enum):
    EDUCATION = "Education"
    HEALTHCARE = "Healthcare"
    COMPANY = "Company"
    ARCHIVE = "Archive"
    NONPROFIT = "Nonprofit"
    GOVERNMENT = "Government"
    FACILITY = "Facility"
    OTHER = "Other"


class Label(BaseModel):
    label: Optional[str] = None
    iso639: Optional[str] = None


class RelationshipType(str, Enum):
    PARENT = "parent"
    RELATED = "related"
    CHILD = "child"
    OTHER = "other"


class RelatedOrgIdentifier(BaseModel):
    idtype: str
    value: str


class Relationship(BaseModel):
    identifiers: Optional[List[RelatedOrgIdentifier]] = None
    type: Optional[RelationshipType] = None
    label: Optional[str] = None
    id: Optional[str] = None


class GeonamesAdmin(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    ascii_name: Optional[str] = None


class NutsLevel(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    ascii_name: Optional[str] = None


class GeonamesCity(BaseModel):
    id: Optional[int] = None
    city: Optional[str] = None
    geonames_admin1: Optional[GeonamesAdmin] = None
    geonames_admin2: Optional[GeonamesAdmin] = None
    nuts_level1: Optional[NutsLevel] = None
    nuts_level2: Optional[NutsLevel] = None
    nuts_level3: Optional[NutsLevel] = None


class Address(BaseModel):
    city: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    line_1: Optional[str] = None
    line_2: Optional[str] = None
    line_3: Optional[str] = None
    postcode: Optional[str] = None
    primary: Optional[bool] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    municipality: Optional[str] = None
    municipality_dpa: Optional[str] = None
    geonames_city: Optional[GeonamesCity] = None

    class Config:
        extra = "allow"


class Redirect(BaseModel):
    idtype: Optional[str] = None
    value: Optional[str] = None


class OrganizationFull(BaseModel):
    id: str
    identifiers: List[Identifier]
    name: str
    status: Optional[OrgStatus] = None
    aliases: Optional[List[str]] = None
    acronyms: Optional[List[str]] = None
    types: Optional[List[OrgType]] = None
    wikipedia_url: Optional[str] = None
    email_address: Optional[str] = None
    ip_addresses: Optional[List[str]] = None
    established: Optional[int] = None
    onei_registry: Optional[int] = None
    exportable: Optional[bool] = None
    research_activity: Optional[bool] = None
    links: Optional[List[str]] = None
    labels: Optional[List[Label]] = None
    relationships: Optional[List[Relationship]] = None
    addresses: List[Address]
    redirect: Optional[Redirect] = None

    class Config:
        extra = "allow"


## Outputs

class Country(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None


class Publication(BaseModel):
    identifiers: Optional[List[Identifier]] = None
    id: Optional[str] = None
    title: Optional[str] = None
    roles: Optional[List[str]] = None
    status: Optional[str] = None


class SourceRelation(BaseModel):
    identifiers: Optional[List[Identifier]] = None
    id: Optional[str] = None
    name: Optional[str] = None
    roles: Optional[List[str]] = None


class Person(BaseModel):
    id: str
    identifiers: List[Identifier]
    name: str
    last_name: Optional[str] = None
    public: Optional[bool] = None
    active: Optional[bool] = None
    gender: Optional[str] = None
    country: Optional[Country] = None
    email_addresses: Optional[List[str]] = None
    aliases: Optional[List[str]] = None
    research_interests: Optional[List[str]] = None
    key_words: Optional[List[str]] = None
    academic_titles: Optional[List[str]] = None
    affiliations: Optional[List[Affiliation]] = None
    roles_sceiba: Optional[List[str]] = None
    publications: Optional[List[Publication]] = None
    sources: Optional[List[SourceRelation]] = None

    class Config:
        extra = "allow"


class PersonId(BaseModel):
    source: str
    value: str


class RecordCreator(BaseModel):
    ids: Optional[List[PersonId]] = None
    name: str
    affiliations: Optional[List[str]] = None
    email: Optional[EmailStr] = None
    roles: Optional[List[str]] = None


class RecordContributor(BaseModel):
    ids: Optional[List[PersonId]] = None
    name: str
    affiliations: Optional[List[str]] = None
    email: Optional[EmailStr] = None
    roles: Optional[List[str]] = None


class RecordDate(BaseModel):
    date: datetime
    info: Optional[str] = None


class Reference(BaseModel):
    raw_reference: Optional[str] = None

    class Config:
        extra = "allow"


class RecordSourceRepo(BaseModel):
    uuid: str
    name: str


class RecordSpec(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None


class Record(BaseModel):
    id: str
    identifiers: List[Identifier]
    source_repo: RecordSourceRepo
    title: str
    spec: Optional[RecordSpec] = None
    creators: Optional[List[RecordCreator]] = None
    keywords: Optional[List[str]] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    sources: Optional[List[str]] = None
    rights: Optional[List[str]] = None
    types: Optional[List[str]] = None
    formats: Optional[List[str]] = None
    language: Optional[str] = None
    publication_date: Optional[datetime] = None
    dates: Optional[List[RecordDate]] = None
    contributors: Optional[List[RecordContributor]] = None
    references: Optional[List[Reference]] = None
    organizations: Optional[List[Organization]] = None
    classifications: Optional[List[Classification]] = None
    terms: Optional[List[str]] = None
    status: Optional[str] = None

    class Config:
        extra = "allow"


