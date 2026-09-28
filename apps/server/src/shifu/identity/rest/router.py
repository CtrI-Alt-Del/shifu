from fastapi import APIRouter

from shifu.identity.rest.controllers.get_current_session_controller import (
    GetCurrentSessionController,
)
from shifu.identity.rest.controllers.get_password_recovery_status_controller import (
    GetPasswordRecoveryStatusController,
)
from shifu.identity.rest.controllers.get_pending_confirmation_status_controller import (
    GetPendingConfirmationStatusController,
)
from shifu.identity.rest.controllers.main_page_entered_controller import (
    MainPageEnteredController,
)
from shifu.identity.rest.controllers.request_password_recovery_controller import (
    RequestPasswordRecoveryController,
)
from shifu.identity.rest.controllers.reset_password_controller import (
    ResetPasswordController,
)
from shifu.identity.rest.controllers.resolve_password_reset_link_controller import (
    ResolvePasswordResetLinkController,
)
from shifu.identity.rest.controllers.retry_password_recovery_controller import (
    RetryPasswordRecoveryController,
)
from shifu.identity.rest.controllers.confirm_account_controller import (
    ConfirmAccountController,
)
from shifu.identity.rest.controllers.register_account_controller import (
    RegisterAccountController,
)
from shifu.identity.rest.controllers.resend_email_confirmation_controller import (
    ResendEmailConfirmationController,
)
from shifu.identity.rest.controllers.sign_in_controller import SignInController
from shifu.identity.rest.controllers.verify_pending_confirmation_context_controller import (
    VerifyPendingConfirmationContextController,
)


class IdentityRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/identity', tags=['identity'])
        SignInController.handle(router)
        GetCurrentSessionController.handle(router)
        MainPageEnteredController.handle(router)
        RegisterAccountController.handle(router)
        ConfirmAccountController.handle(router)
        ResendEmailConfirmationController.handle(router)
        GetPendingConfirmationStatusController.handle(router)
        VerifyPendingConfirmationContextController.handle(router)
        RequestPasswordRecoveryController.handle(router)
        GetPasswordRecoveryStatusController.handle(router)
        RetryPasswordRecoveryController.handle(router)
        ResolvePasswordResetLinkController.handle(router)
        ResetPasswordController.handle(router)
        return router
