from django.core.exceptions import FieldDoesNotExist
from mypy.nodes import TypeInfo
from mypy.plugin import MethodContext
from mypy.types import AnyType, Instance
from mypy.types import Type as MypyType
from mypy.types import TypeOfAny

from mypy_django_plugin.django.context import DjangoContext
from mypy_django_plugin.lib import fullnames, helpers


def _get_field_instance(ctx: MethodContext, field_fullname: str) -> MypyType:
    field_info = helpers.lookup_fully_qualified_typeinfo(helpers.get_typechecker_api(ctx),
                                                         field_fullname)
    assert isinstance(field_info, TypeInfo)
    return Instance(field_info, [AnyType(TypeOfAny.explicit), AnyType(TypeOfAny.explicit)])


def return_proper_field_type_from_get_field(ctx: MethodContext, django_context: DjangoContext) -> MypyType:
    # Options instance
    assert isinstance(ctx.type, Instance)

    model_type = ctx.type.args[0]
    if not isinstance(model_type, Instance):
        return _get_field_instance(ctx, fullnames.FIELD_FULLNAME)

    model_cls = django_context.get_model_class_by_fullname(model_type.type.fullname())
    if model_cls is None:
        return _get_field_instance(ctx, fullnames.FIELD_FULLNAME)

    field_name_expr = helpers.get_call_argument_by_name(ctx, 'field_name')
    if field_name_expr is None:
        return _get_field_instance(ctx, fullnames.FIELD_FULLNAME)

    field_name = helpers.resolve_string_attribute_value(field_name_expr, ctx, django_context)
    if field_name is None:
        return _get_field_instance(ctx, fullnames.FIELD_FULLNAME)

    try:
        field = model_cls._meta.get_field(field_name)
    except FieldDoesNotExist as exc:
        ctx.api.fail(exc.args[0], ctx.context)
        return AnyType(TypeOfAny.from_error)

    field_fullname = helpers.get_class_fullname(field.__class__)
    return _get_field_instance(ctx, field_fullname)
