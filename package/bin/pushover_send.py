"""Splunk custom search command to send one Pushover message."""

try:
    import import_declare_test  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    pass

from splunklib.searchcommands import (  # type: ignore[import-untyped]
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
    validators,
)
from splunktaucclib.splunk_aoblib.setup_util import Setup_Util  # type: ignore

from ta_pushover.pushover_common import (
    PushoverClient,
    extract_account_credentials,
    parse_priority,
)


@Configuration()
class PushoverSendCommand(GeneratingCommand):  # type: ignore[misc]
    account = Option(require=True)
    message = Option(require=True)
    title = Option(require=False, default=None)
    url = Option(require=False, default=None)
    url_title = Option(require=False, default=None)
    priority = Option(require=False, default=0, validate=validators.Integer(-2, 2))
    sound = Option(require=False, default="")

    def generate(self):  # type: ignore[no-untyped-def]
        try:
            if self.service is None:
                raise RuntimeError(
                    "Search command is missing service context. "
                    "Ensure commands.conf has requires_srinfo=true."
                )

            searchinfo = self.metadata.searchinfo
            setup_util = Setup_Util(
                searchinfo.splunkd_uri,
                searchinfo.session_key,
                self.logger,
            )
            account_record = setup_util.get_credential_by_id(str(self.account))
            if account_record is None:
                raise ValueError(f"Account '{self.account}' was not found")

            user_key, app_token = extract_account_credentials(account_record)

            response = PushoverClient(logger=self.logger).send(
                token=app_token,
                user=user_key,
                message=str(self.message),
                title=self.title,
                url=self.url,
                url_title=self.url_title,
                priority=parse_priority(self.priority, 0),
                sound=self.sound,
            )
            yield {
                "status": "success",
                "account": str(self.account),
                "request_id": str(response.get("request", "")),
                "api_status": str(response.get("status", "")),
            }
        except Exception as error:  # pylint: disable=broad-except
            self.logger.exception("Failed to send Pushover message")
            yield {
                "status": "error",
                "account": str(self.account),
                "error": str(error),
            }


dispatch(PushoverSendCommand, module_name=__name__)
