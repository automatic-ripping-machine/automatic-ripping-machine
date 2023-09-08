from datetime import datetime
from pydoc import text

from pydantic import BaseModel
from typing import List
from pydantic.schema import Optional, Dict


class CreateAndUpdateTrack(BaseModel):
    track_id: int
    job_id: int
    track_number: str
    length: int
    aspect_ratio: str
    fps: float
    main_feature: Optional[bool]
    basename: str
    filename: str
    orig_filename: Optional[str]
    new_filename: Optional[str]
    ripped: Optional[bool]
    status: Optional[str]
    error: Optional[str]
    source: str


class TrackSchemas(CreateAndUpdateTrack):
    track_id: int

    class Config:
        orm_mode = True


class CreateAndUpdateConfig(BaseModel):
    job_id: Optional[int]
    CONFIG_ID: Optional[int]
    ARM_CHECK_UDF: bool
    GET_VIDEO_TITLE: bool
    SKIP_TRANSCODE: bool
    VIDEOTYPE: str
    MINLENGTH: str
    MAXLENGTH: str
    MANUAL_WAIT: bool
    MANUAL_WAIT_TIME: int
    RAW_PATH: str
    TRANSCODE_PATH: str
    COMPLETED_PATH: str
    EXTRAS_SUB: str
    INSTALLPATH: str
    LOGPATH: str
    LOGLEVEL: str
    LOGLIFE: int
    DBFILE: str
    WEBSERVER_IP: str
    WEBSERVER_PORT: int
    SET_MEDIA_PERMISSIONS: bool
    CHMOD_VALUE: int
    SET_MEDIA_OWNER: bool
    CHOWN_USER: Optional[str]
    CHOWN_GROUP: Optional[str]
    RIPMETHOD: str
    MKV_ARGS: str
    DELRAWFILES: bool
    HASHEDKEYS: Optional[bool]
    HB_PRESET_DVD: str
    HB_PRESET_BD: str
    DEST_EXT: str
    HANDBRAKE_CLI: str
    MAINFEATURE: bool
    HB_ARGS_DVD: str
    HB_ARGS_BD: str
    EMBY_REFRESH: bool
    EMBY_SERVER: str
    EMBY_PORT: str
    EMBY_CLIENT: str
    EMBY_DEVICE: str
    EMBY_DEVICEID: str
    EMBY_USERNAME: str
    EMBY_USERID: str
    EMBY_PASSWORD: str
    EMBY_API_KEY: str
    NOTIFY_RIP: bool
    NOTIFY_TRANSCODE: bool
    PB_KEY: str
    IFTTT_KEY: str
    IFTTT_EVENT: str
    PO_USER_KEY: str
    PO_APP_KEY: str
    OMDB_API_KEY: str


class ConfigSchemas(CreateAndUpdateConfig):
    CONFIG_ID: int

    class Config:
        orm_mode = True


# TO support creation and update APIs
class CreateAndUpdateJob(BaseModel):
    config: ConfigSchemas
    tracks: Optional[List[TrackSchemas]]
    arm_version: str
    crc_id: Optional[str]
    logfile: str
    start_time: datetime
    stop_time: Optional[datetime]
    job_length: Optional[str]
    status: str
    stage: str
    no_of_titles: Optional[int]
    title: str
    title_auto: Optional[str]
    title_manual: Optional[str]
    year: str
    year_auto: Optional[str]
    year_manual: Optional[str]
    video_type: str
    video_type_auto: Optional[str]
    video_type_manual: Optional[str]
    imdb_id: str
    imdb_id_auto: Optional[str]
    imdb_id_manual: Optional[str]
    poster_url: str
    poster_url_auto: Optional[str]
    poster_url_manual: Optional[str]
    devpath: str
    mountpoint: str
    hasnicetitle: bool
    errors: Optional[str]
    disctype: str
    label: str
    path: Optional[str]
    ejected: bool
    updated: bool
    pid: int
    pid_hash: int


# TO support list and get APIs
class JobSchemas(CreateAndUpdateJob):
    job_id: int

    class Config:
        orm_mode = True


# To support list Jobs API
class PaginatedJobList(BaseModel):
    limit: int
    offset: int
    results: List[JobSchemas]


class CreateAndUpdateUISettings(BaseModel):
    use_icons: bool
    save_remote_images: bool
    bootstrap_skin: str
    language: str
    index_refresh: int
    database_limit: int
    notify_refresh: int


class UISettingsSchemas(CreateAndUpdateUISettings):
    id: int

    class Config:
        orm_mode = True


class CreateAndUpdateUser(BaseModel):
    user_id: int
    username: str
    password: str
    hash: str
    disabled: bool


class UserSchemas(CreateAndUpdateUser):
    id: int

    class Config:
        orm_mode = True


class CreateAndUpdateRipper(BaseModel):
    ARM_NAME: Optional[str]
    ARM_CHILDREN: Optional[str]
    PREVENT_99: int
    ARM_CHECK_UDF: int
    UMASK: str
    GET_VIDEO_TITLE: int
    ARM_API_KEY: Optional[str]
    DISABLE_LOGIN: int
    SKIP_TRANSCODE: int
    VIDEOTYPE: str
    MINLENGTH: int
    MAXLENGTH: int
    MANUAL_WAIT: int
    MANUAL_WAIT_TIME: int
    DATE_FORMAT: str
    ALLOW_DUPLICATES: int
    MAX_CONCURRENT_TRANSCODES: int
    DATA_RIP_PARAMETERS: Optional[str]
    METADATA_PROVIDER: str
    GET_AUDIO_TITLE: str
    RIP_POSTER: int
    ABCDE_CONFIG_FILE: str
    RAW_PATH: str
    TRANSCODE_PATH: str
    COMPLETED_PATH: str
    EXTRAS_SUB: str
    INSTALLPATH: str
    LOGPATH: str
    LOGLEVEL: str
    LOGLIFE: int
    DBFILE: str
    WEBSERVER_IP: str
    WEBSERVER_PORT: int
    SET_MEDIA_PERMISSIONS: int
    CHMOD_VALUE: int
    SET_MEDIA_OWNER: int
    CHOWN_USER: Optional[str]
    CHOWN_GROUP: Optional[str]
    MAKEMKV_PERMA_KEY: Optional[str]
    RIPMETHOD: str
    RIPMETHOD_DVD: str
    RIPMETHOD_BR: str
    MKV_ARGS: Optional[str]
    DELRAWFILES: int
    HB_PRESET_DVD: str
    HB_PRESET_BD: str
    DEST_EXT: str
    HANDBRAKE_CLI: str
    HANDBRAKE_LOCAL: str
    MAINFEATURE: int
    HB_ARGS_DVD: str
    HB_ARGS_BD: str
    EMBY_REFRESH: int
    EMBY_SERVER: Optional[str]
    EMBY_PORT: int
    EMBY_CLIENT: str
    EMBY_DEVICE: str
    EMBY_DEVICEID: str
    EMBY_USERNAME: Optional[str]
    EMBY_USERID: Optional[str]
    EMBY_PASSWORD: Optional[str]
    EMBY_API_KEY: Optional[str]
    NOTIFY_RIP: int
    NOTIFY_TRANSCODE: int
    NOTIFY_JOBID: int
    PB_KEY: Optional[str]
    IFTTT_KEY: Optional[str]
    IFTTT_EVENT: Optional[str]
    PO_USER_KEY: Optional[str]
    PO_APP_KEY: Optional[str]
    OMDB_API_KEY: Optional[str]
    TMDB_API_KEY: Optional[str]
    JSON_URL: Optional[str]
    APPRISE: Optional[str]


class RipperSchemas(CreateAndUpdateRipper):
    id: int

    class Config:
        orm_mode = True



class CreateAndUpdateApprise(BaseModel):
    BOXCAR_KEY: Optional[str]
    BOXCAR_SECRET: Optional[str]
    DISCORD_WEBHOOK_ID: Optional[str]
    DISCORD_TOKEN: Optional[str]
    FAAST_TOKEN: Optional[str]
    FLOCK_TOKEN: Optional[str]
    GITTER_TOKEN: Optional[str]
    GITTER_ROOM: Optional[str]
    GOTIFY_TOKEN: Optional[str]
    GOTIFY_HOST: Optional[str]
    GROWL_HOST: Optional[str]
    GROWL_PASS: Optional[str]
    JOIN_API: Optional[str]
    JOIN_DEVICE: Optional[str]
    KODI_HOST: Optional[str]
    KODI_PORT: Optional[str]
    KODI_USER: Optional[str]
    KODI_PASS: Optional[str]
    KUMULOS_API: Optional[str]
    KUMULOS_SERVERKEY: Optional[str]
    LAMETRIC_MODE: Optional[str]
    LAMETRIC_API: Optional[str]
    LAMETRIC_HOST: Optional[str]
    LAMETRIC_APP_ID: Optional[str]
    LAMETRIC_TOKEN: Optional[str]
    MAILGUN_DOMAIN: Optional[str]
    MAILGUN_USER: Optional[str]
    MAILGUN_APIKEY: Optional[str]
    MATRIX_HOST: Optional[str]
    MATRIX_USER: Optional[str]
    MATRIX_PASS: Optional[str]
    MATRIX_TOKEN: Optional[str]
    MSTEAMS_TOKENA: Optional[str]
    MSTEAMS_TOKENB: Optional[str]
    MSTEAMS_TOKENC: Optional[str]
    NEXTCLOUD_HOST: Optional[str]
    NEXTCLOUD_ADMINUSER: Optional[str]
    NEXTCLOUD_ADMINPASS: Optional[str]
    NEXTCLOUD_NOTIFY_USER: Optional[str]
    NOTICA_TOKEN: Optional[str]
    NOTIFICO_PROJECTID: Optional[str]
    NOTIFICO_MESSAGEHOOK: Optional[str]
    OFFICE365_TENANTID: Optional[str]
    OFFICE365_ACCOUNTEMAIL: Optional[str]
    OFFICE365_CLIENT_ID: Optional[str]
    OFFICE365_CLIENT_SECRET: Optional[str]
    POPCORN_API: Optional[str]
    POPCORN_EMAIL: Optional[str]
    POPCORN_PHONENO: Optional[str]
    PROWL_API: Optional[str]
    PROWL_PROVIDERKEY: Optional[str]
    PUSHJET_HOST: Optional[str]
    PUSHJET_SECRET: Optional[str]
    PUSH_API: Optional[str]
    PUSHED_APP_KEY: Optional[str]
    PUSHED_APP_SECRET: Optional[str]
    PUSHSAFER_KEY: Optional[str]
    ROCKETCHAT_HOST: Optional[str]
    ROCKETCHAT_USER: Optional[str]
    ROCKETCHAT_PASS: Optional[str]
    ROCKETCHAT_WEBHOOK: Optional[str]
    RYVER_ORG: Optional[str]
    RYVER_TOKEN: Optional[str]
    SENDGRID_API: Optional[str]
    SENDGRID_FROMMAIL: Optional[str]
    SIMPLEPUSH_API: Optional[str]
    SLACK_TOKENA: Optional[str]
    SLACK_TOKENB: Optional[str]
    SLACK_TOKENC: Optional[str]
    SLACK_CHANNEL: Optional[str]
    SPARKPOST_API: Optional[str]
    SPARKPOST_HOST: Optional[str]
    SPARKPOST_USER: Optional[str]
    SPARKPOST_EMAIL: Optional[str]
    SPONTIT_API: Optional[str]
    SPONTIT_USER_ID: Optional[str]
    TELEGRAM_BOT_TOKEN: Optional[str]
    TELEGRAM_CHAT_ID: Optional[str]
    TWIST_EMAIL: Optional[str]
    TWIST_PASS: Optional[str]
    XBMC_HOST: Optional[str]
    XBMC_PORT: Optional[str]
    XBMC_USER: Optional[str]
    XBMC_PASS: Optional[str]
    XMPP_HOST: Optional[str]
    XMPP_PASS: Optional[str]
    XMPP_USER: Optional[str]
    WEBEX_TEAMS_TOKEN: Optional[str]
    ZILUP_CHAT_TOKEN: Optional[str]
    ZILUP_CHAT_BOTNAME: Optional[str]
    ZILUP_CHAT_ORG: Optional[str]


class AppriseSchemas(CreateAndUpdateApprise):
    id: int

    class Config:
        orm_mode = True

class UpdatePassword(BaseModel):
    username: str
    old_password: str
    new_password: str
