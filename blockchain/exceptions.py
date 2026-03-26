# coding:utf-8


class ValidationError(Exception):
    pass


class DoubleSpendError(ValidationError):
    pass


class InvalidAddressError(ValidationError):
    pass


class SignatureError(ValidationError):
    pass


class InsufficientFundsError(ValidationError):
    pass


class AmountError(ValidationError):
    pass


class UTXONotFoundError(ValidationError):
    pass


class TransactionError(ValidationError):
    pass


class WalletLockedError(ValidationError):
    pass


class InvalidPasswordError(ValidationError):
    pass
