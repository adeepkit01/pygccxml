# Copyright 2014-2016 Insight Software Consortium.
# Copyright 2004-2008 Roman Yakovenko.
# Distributed under the Boost Software License, Version 1.0.
# See http://www.boost.org/LICENSE_1_0.txt

"""
defines few algorithms, that deals with different C++ type properties

Are you aware of `boost::type_traits <http://www.boost.org/doc/libs/1_37_0/
libs/type_traits/doc/html/boost_typetraits/intro.html>`_
library? pygccxml implements the same functionality.

This module contains a set of very specific traits functions\\classes, each of
which encapsulate a single trait from the C++ type system. For example:
* is a type a pointer or a reference type ?
* does a type have a trivial constructor ?
* does a type have a const-qualifier ?

"""

import os

from . import matchers
from . import calldef
from . import calldef_members
from . import cpptypes
from . import algorithm
from . import namespace
from . import scopedef
from . import templates
from . import enumeration
from . import class_declaration
from . import type_traits_utils
from .. import utils


def create_cv_types(base):
    """implementation details"""
    return (
        [base,
         cpptypes.const_t(
             base),
            cpptypes.volatile_t(base),
            cpptypes.volatile_t(cpptypes.const_t(base))]
    )


def does_match_definition(given, main, secondary):
    """implementation details"""
    assert isinstance(secondary, tuple)
    assert 2 == len(secondary)  # general solution could be provided
    types = type_traits_utils.decompose_type(given)
    if isinstance(types[0], main):
        return True
    elif 2 <= len(types) and \
        ((isinstance(types[0], main) and isinstance(types[1], secondary)) or
            (isinstance(types[1], main) and isinstance(types[0], secondary))):
        return True
    elif 3 <= len(types):
        classes = set([tp.__class__ for tp in types[:3]])
        desired = set([main] + list(secondary))
        diff = classes.symmetric_difference(desired)
        if not diff:
            return True
        if len(diff) == 2:
            items = list(diff)
            return (
                issubclass(
                    items[0], items[1]) or issubclass(items[1], items[0]))
        else:
            return False
    else:
        return False


def is_bool(type_):
    """returns True, if type represents `bool`, False otherwise"""
    return type_traits_utils.remove_alias(type_) in create_cv_types(
        cpptypes.bool_t())


def is_void(type):
    """returns True, if type represents `void`, False otherwise"""
    return type_traits_utils.remove_alias(type) in create_cv_types(
        cpptypes.void_t())


def is_void_pointer(type):
    """returns True, if type represents `void*`, False otherwise"""
    return is_same(type, cpptypes.pointer_t(cpptypes.void_t()))


def is_integral(type):
    """returns True, if type represents C++ integral type, False otherwise"""
    integral_def = (
        create_cv_types(cpptypes.char_t()) +
        create_cv_types(cpptypes.unsigned_char_t()) +
        create_cv_types(cpptypes.signed_char_t()) +
        create_cv_types(cpptypes.wchar_t()) +
        create_cv_types(cpptypes.short_int_t()) +
        create_cv_types(cpptypes.short_unsigned_int_t()) +
        create_cv_types(cpptypes.bool_t()) +
        create_cv_types(cpptypes.int_t()) +
        create_cv_types(cpptypes.unsigned_int_t()) +
        create_cv_types(cpptypes.long_int_t()) +
        create_cv_types(cpptypes.long_unsigned_int_t()) +
        create_cv_types(cpptypes.long_long_int_t()) +
        create_cv_types(cpptypes.long_long_unsigned_int_t()) +
        create_cv_types(cpptypes.int128_t()) +
        create_cv_types(cpptypes.uint128_t()))

    return type_traits_utils.remove_alias(type) in integral_def


def is_floating_point(type):
    """returns True, if type represents C++ floating point type,
    False otherwise"""
    float_def = (
        create_cv_types(cpptypes.float_t()) +
        create_cv_types(cpptypes.double_t()) +
        create_cv_types(cpptypes.long_double_t()))

    return type_traits_utils.remove_alias(type) in float_def


def is_arithmetic(type):
    """returns True, if type represents C++ integral or floating point type,
    False otherwise"""
    return is_integral(type) or is_floating_point(type)


def is_pointer(type):
    """returns True, if type represents C++ pointer type, False otherwise"""
    return does_match_definition(type,
                                 cpptypes.pointer_t,
                                 (cpptypes.const_t, cpptypes.volatile_t)) \
        or does_match_definition(type,
                                 cpptypes.pointer_t,
                                 (cpptypes.volatile_t, cpptypes.const_t))


def is_calldef_pointer(type):
    """returns True, if type represents pointer to free/member function,
    False otherwise"""
    if not is_pointer(type):
        return False
    nake_type = type_traits_utils.remove_alias(type)
    nake_type = remove_cv(nake_type)
    return isinstance(nake_type, cpptypes.compound_t) \
        and isinstance(nake_type.base, cpptypes.calldef_type_t)


def remove_pointer(type):
    """removes pointer from the type definition

    If type is not pointer type, it will be returned as is.
    """
    nake_type = type_traits_utils.remove_alias(type)
    if not is_pointer(nake_type):
        return type
    elif isinstance(nake_type, cpptypes.volatile_t) and \
            isinstance(nake_type.base, cpptypes.pointer_t):
        return cpptypes.volatile_t(nake_type.base.base)
    elif isinstance(nake_type, cpptypes.const_t) and \
            isinstance(nake_type.base, cpptypes.pointer_t):
        return cpptypes.const_t(nake_type.base.base)
    elif isinstance(nake_type, cpptypes.volatile_t) \
            and isinstance(nake_type.base, cpptypes.const_t) \
            and isinstance(nake_type.base.base, cpptypes.pointer_t):
        return (
            cpptypes.volatile_t(cpptypes.const_t(nake_type.base.base.base))
        )
    elif isinstance(nake_type.base, cpptypes.calldef_type_t):
        return type
    else:
        return nake_type.base


def is_reference(type):
    """returns True, if type represents C++ reference type, False otherwise"""
    nake_type = type_traits_utils.remove_alias(type)
    return isinstance(nake_type, cpptypes.reference_t)


def is_array(type):
    """returns True, if type represents C++ array type, False otherwise"""
    nake_type = type_traits_utils.remove_alias(type)
    nake_type = remove_reference(nake_type)
    nake_type = remove_cv(nake_type)
    return isinstance(nake_type, cpptypes.array_t)


def array_size(type):
    """returns array size"""
    nake_type = type_traits_utils.remove_alias(type)
    nake_type = remove_reference(nake_type)
    nake_type = remove_cv(nake_type)
    assert isinstance(nake_type, cpptypes.array_t)
    return nake_type.size


def array_item_type(type_):
    """returns array item type"""
    if is_array(type_):
        type_ = type_traits_utils.remove_alias(type_)
        type_ = remove_cv(type_)
        return type_.base
    elif is_pointer(type_):
        return remove_pointer(type_)
    else:
        raise RuntimeError(
            "array_item_type functions takes as argument array or pointer " +
            "types")


def remove_reference(type):
    """removes reference from the type definition

    If type is not reference type, it will be returned as is.
    """
    nake_type = type_traits_utils.remove_alias(type)
    if not is_reference(nake_type):
        return type
    else:
        return nake_type.base


def is_const(type):
    """returns True, if type represents C++ const type, False otherwise"""
    nake_type = type_traits_utils.remove_alias(type)
    if isinstance(nake_type, cpptypes.const_t):
        return True
    elif isinstance(nake_type, cpptypes.volatile_t):
        return is_const(nake_type.base)
    elif isinstance(nake_type, cpptypes.array_t):
        return is_const(nake_type.base)
    return False


def remove_const(type_):
    """removes const from the type definition

    If type is not const type, it will be returned as is
    """

    nake_type = type_traits_utils.remove_alias(type_)
    if not is_const(nake_type):
        return type_
    else:
        # Handling for const and volatile qualified types. There is a
        # difference in behavior between GCCXML and CastXML for cv-qual arrays.
        # GCCXML produces the following nesting of types:
        #       ->  volatile_t(const_t(array_t))
        # while CastXML produces the following nesting:
        #       ->  array_t(volatile_t(const_t))
        # For both cases, we must unwrap the types, remove const_t, and add
        # back the outer layers
        if isinstance(nake_type, cpptypes.array_t):
            is_v = is_volatile(nake_type)
            if is_v:
                result_type = nake_type.base.base.base
            else:
                result_type = nake_type.base.base
            if is_v:
                result_type = cpptypes.volatile_t(result_type)
            return cpptypes.array_t(result_type, nake_type.size)

        elif isinstance(nake_type, cpptypes.volatile_t):
            return cpptypes.volatile_t(nake_type.base.base)

        return nake_type.base


def remove_declarated(type_):
    """removes type-declaration class-binder :class:`declarated_t` from
    the `type_`

    If `type_` is not :class:`declarated_t`, it will be returned as is
    """
    type_ = type_traits_utils.remove_alias(type_)
    if isinstance(type_, cpptypes.declarated_t):
        type_ = type_.declaration
    return type_


def is_same(type1, type2):
    """returns True, if type1 and type2 are same types"""
    nake_type1 = remove_declarated(type1)
    nake_type2 = remove_declarated(type2)
    return nake_type1 == nake_type2


def is_volatile(type):
    """returns True, if type represents C++ volatile type, False otherwise"""
    nake_type = type_traits_utils.remove_alias(type)
    if isinstance(nake_type, cpptypes.volatile_t):
        return True
    elif isinstance(nake_type, cpptypes.const_t):
        return is_volatile(nake_type.base)
    elif isinstance(nake_type, cpptypes.array_t):
        return is_volatile(nake_type.base)
    return False


def remove_volatile(type):
    """removes volatile from the type definition

    If type is not volatile type, it will be returned as is
    """
    nake_type = type_traits_utils.remove_alias(type)
    if not is_volatile(nake_type):
        return type
    else:
        if isinstance(nake_type, cpptypes.array_t):
            is_c = is_const(nake_type)
            if is_c:
                base_type = nake_type.base.base.base
            else:
                base_type = nake_type.base.base
            result_type = base_type
            if is_c:
                result_type = cpptypes.const_t(result_type)
            return cpptypes.array_t(result_type, nake_type.size)
        return nake_type.base


def remove_cv(type):
    """removes const and volatile from the type definition"""

    nake_type = type_traits_utils.remove_alias(type)
    if not is_const(nake_type) and not is_volatile(nake_type):
        return type
    result = nake_type
    if is_const(result):
        result = remove_const(result)
    if is_volatile(result):
        result = remove_volatile(result)
    if is_const(result):
        result = remove_const(result)
    return result


def is_fundamental(type):
    """returns True, if type represents C++ fundamental type"""
    return does_match_definition(
        type,
        cpptypes.fundamental_t,
        (cpptypes.const_t, cpptypes.volatile_t)) \
        or does_match_definition(
            type,
            cpptypes.fundamental_t,
            (cpptypes.volatile_t, cpptypes.const_t))


def is_union(type_):
    """returns True if type represents a C++ union"""
    if not is_class(type_):
        return False
    decl = class_traits.get_declaration(type_)
    return decl.class_type == class_declaration.CLASS_TYPES.UNION


class declaration_xxx_traits(object):
    """this class implements the functionality needed for convenient work with
    declaration classes

    Implemented functionality:
        - find out whether a declaration is a desired one
        - get reference to the declaration
    """
    sequence = [type_traits_utils.remove_alias, remove_cv, remove_declarated]

    def __init__(self, declaration_class):
        self.declaration_class = declaration_class

    def __apply_sequence(self, type_):
        for f in self.sequence:
            type_ = f(type_)
        return type_

    def is_my_case(self, type_):
        """returns True, if type represents the desired declaration,
        False otherwise"""
        return (
            isinstance(self.__apply_sequence(type_), self.declaration_class)
        )

    def get_declaration(self, type_):
        """returns reference to the declaration

        Precondition: self.is_my_case( type ) == True
        """
        return self.__apply_sequence(type_)

enum_traits = declaration_xxx_traits(enumeration.enumeration_t)
"""implements functionality, needed for convenient work with C++ enums"""

is_enum = enum_traits.is_my_case
"""returns True, if type represents C++ enumeration declaration,
False otherwise"""

enum_declaration = enum_traits.get_declaration
"""returns reference to enum declaration"""

class_traits = declaration_xxx_traits(class_declaration.class_t)
"""implements functionality, needed for convenient work with C++ classes"""

is_class = class_traits.is_my_case
"""returns True, if type represents C++ class definition, False otherwise"""

class_declaration_traits = declaration_xxx_traits(
    class_declaration.class_declaration_t)
"""implements functionality, needed for convenient work with C++ class
declarations"""

is_class_declaration = class_declaration_traits.is_my_case
"""returns True, if type represents C++ class declaration, False otherwise"""


def find_trivial_constructor(type_):
    """returns reference to trivial constructor or None"""
    assert isinstance(type_, class_declaration.class_t)
    return type_.find_trivial_constructor()


def has_trivial_constructor(class_):
    """if class has public trivial constructor, this function will return
    reference to it, None otherwise"""
    class_ = class_traits.get_declaration(class_)
    trivial = class_.find_trivial_constructor()
    if trivial and trivial.access_type == 'public':
        return trivial


def has_copy_constructor(class_):
    """if class has public copy constructor, this function will return
    reference to it, None otherwise"""
    class_ = class_traits.get_declaration(class_)
    copy_constructor = class_.find_copy_constructor()
    if copy_constructor and copy_constructor.access_type == 'public':
        return copy_constructor


def has_destructor(class_):
    """if class has destructor, this function will return reference to it,
    None otherwise"""
    class_ = class_traits.get_declaration(class_)
    destructor = class_.decls(
        decl_type=calldef_members.destructor_t,
        recursive=False,
        allow_empty=True)
    if destructor:
        return destructor[0]


def has_public_constructor(class_):
    """if class has any public constructor, this function will return list of
    them, otherwise None"""
    class_ = class_traits.get_declaration(class_)
    decls = class_.constructors(
        lambda c: not c.is_copy_constructor and c.access_type == 'public',
        recursive=False,
        allow_empty=True)
    if decls:
        return decls


def has_public_assign(class_):
    """returns True, if class has public assign operator, False otherwise"""
    class_ = class_traits.get_declaration(class_)
    decls = class_.mem_opers(
        lambda o: o.symbol == '=' and o.access_type == 'public',
        recursive=False,
        allow_empty=True)
    return bool(decls)


def has_public_destructor(type):
    """returns True, if class has public destructor, False otherwise"""
    d = has_destructor(type)
    return d and d.access_type == 'public'


def is_base_and_derived(based, derived):
    """returns True, if there is "base and derived" relationship between
    classes, False otherwise"""
    assert isinstance(based, class_declaration.class_t)
    assert isinstance(derived, (class_declaration.class_t, tuple))

    if isinstance(derived, class_declaration.class_t):
        all_derived = ([derived])
    else:  # tuple
        all_derived = derived

    for derived_cls in all_derived:
        for base_desc in derived_cls.recursive_bases:
            if base_desc.related_class == based:
                return True
    return False


def has_any_non_copyconstructor(type):
    """if class has any public constructor, which is not copy constructor,
    this function will return list of them, otherwise None"""
    class_ = class_traits.get_declaration(type)
    decls = class_.constructors(
        lambda c: not c.is_copy_constructor and c.access_type == 'public',
        recursive=False,
        allow_empty=True)
    if decls:
        return decls


def has_public_binary_operator(type_, operator_symbol):
    """returns True, if `type_` has public binary operator, otherwise False"""
    type_ = type_traits_utils.remove_alias(type_)
    type_ = remove_cv(type_)
    type_ = remove_declarated(type_)
    assert isinstance(type_, class_declaration.class_t)

    if is_std_string(type_) or is_std_wstring(type_):
        # In some case compare operators of std::basic_string are not
        # instantiated
        return True

    operators = type_.member_operators(
        function=matchers.custom_matcher_t(
            lambda decl: not decl.is_artificial) &
        matchers.access_type_matcher_t('public'),
        symbol=operator_symbol, allow_empty=True, recursive=False)
    if operators:
        return True

    t = cpptypes.declarated_t(type_)
    t = cpptypes.const_t(t)
    t = cpptypes.reference_t(t)
    operators = type_.top_parent.operators(
        function=lambda decl: not decl.is_artificial,
        arg_types=[t, None],
        symbol=operator_symbol,
        allow_empty=True,
        recursive=True)
    if operators:
        return True
    for bi in type_.recursive_bases:
        assert isinstance(bi, class_declaration.hierarchy_info_t)
        if bi.access_type != class_declaration.ACCESS_TYPES.PUBLIC:
            continue
        operators = bi.related_class.member_operators(
            function=matchers.custom_matcher_t(
                lambda decl: not decl.is_artificial) &
            matchers.access_type_matcher_t('public'),
            symbol=operator_symbol, allow_empty=True, recursive=False)
        if operators:
            return True
    return False


def has_public_equal(type):
    """returns True, if class has public operator==, otherwise False"""
    return has_public_binary_operator(type, '==')


def has_public_less(type):
    """returns True, if class has public operator<, otherwise False"""
    return has_public_binary_operator(type, '<')


def is_unary_operator(oper):
    """returns True, if operator is unary operator, otherwise False"""
    # definition:
    # memeber in class
    # ret-type operator symbol()
    # ret-type operator [++ --](int)
    # globally
    # ret-type operator symbol( arg )
    # ret-type operator [++ --](X&, int)
    symbols = ['!', '&', '~', '*', '+', '++', '-', '--']
    if not isinstance(oper, calldef_members.operator_t):
        return False
    if oper.symbol not in symbols:
        return False
    if isinstance(oper, calldef_members.member_operator_t):
        if 0 == len(oper.arguments):
            return True
        elif oper.symbol in ['++', '--'] and \
                isinstance(oper.arguments[0].decl_type, cpptypes.int_t):
            return True
        else:
            return False
    else:
        if 1 == len(oper.arguments):
            return True
        elif oper.symbol in ['++', '--'] \
                and 2 == len(oper.arguments) \
                and isinstance(oper.arguments[1].decl_type, cpptypes.int_t):
            # may be I need to add additional check whether first argument is
            # reference or not?
            return True
        else:
            return False


def is_binary_operator(oper):
    """returns True, if operator is binary operator, otherwise False"""
    # definition:
    # memeber in class
    # ret-type operator symbol(arg)
    # globally
    # ret-type operator symbol( arg1, arg2 )
    symbols = [
        ',', '()', '[]', '!=', '%', '%=', '&', '&&', '&=', '*', '*=', '+',
        '+=', '-', '-=', '->', '->*', '/', '/=', '<', '<<', '<<=', '<=', '=',
        '==', '>', '>=', '>>', '>>=', '^', '^=', '|', '|=', '||']
    if not isinstance(oper, calldef_members.operator_t):
        return False
    if oper.symbol not in symbols:
        return False
    if isinstance(oper, calldef_members.member_operator_t):
        if 1 == len(oper.arguments):
            return True
        else:
            return False
    else:
        if 2 == len(oper.arguments):
            return True
        else:
            return False


class __is_convertible_t(object):

    """implementation details"""

    def __init__(self, source, target):
        self.__source = self.__normalize(source)
        self.__target = self.__normalize(target)

    def __find_class_by_class_declaration(self, class_decl):
        found = scopedef.find_declaration(
            class_decl.parent.declarations,
            name=class_decl.name,
            decl_type=class_declaration.class_t)
        return found

    def __normalize(self, type_):
        type_ = type_traits_utils.remove_alias(type_)
        bt_of_type = type_traits_utils.base_type(type_)
        if isinstance(bt_of_type, cpptypes.declarated_t) \
           and isinstance(bt_of_type.declaration,
                          class_declaration.class_declaration_t):
            type_ = type_.clone()
            bt_of_type = type_traits_utils.base_type(type_)
            bt_of_type.declaration = self.__find_class_by_class_declaration(
                bt_of_type.declaration)
        return type_

    def __test_trivial(self, source, target):
        if not (source and target):
            return False
        if is_same(source, target):
            return True  # X => X
        if is_const(target) and is_same(source, target.base):
            return True  # X => const X
        if is_reference(target) and is_same(source, target.base):
            return True  # X => X&
        if is_reference(target) and is_const(target.base) and \
                is_same(source, target.base.base):
            return True  # X => const X&
        if is_same(target, cpptypes.pointer_t(cpptypes.void_t())):
            if is_integral(source) or is_enum(source):
                return False
            else:
                return True  # X => void*
        if is_pointer(source) and is_pointer(target):
            if is_const(target.base) and \
                    is_same(source.base, target.base.base):
                return True  # X* => const X*
        if is_reference(source) and is_reference(target):
            if is_const(target.base) and \
                    is_same(source.base, target.base.base):
                return True  # X& => const X&
        if not is_const(source) and is_array(source) and is_pointer(target):
            if is_same(type_traits_utils.base_type(source), target.base):
                return True  # X[2] => X*
        if is_array(source) and is_pointer(target) and is_const(target.base):
            if is_same(type_traits_utils.base_type(source), target.base.base):
                return True

    def __test_pointer_to_func_or_mv__to__func_or_mv(self, source, target):
        if is_pointer(source) \
           and is_reference(target) \
           and isinstance(target.base,
                          (cpptypes.free_function_type_t,
                           cpptypes.member_function_type_t,
                           cpptypes.member_variable_type_t)) \
           and is_same(source.base, target.base):
            return True

        if is_pointer(source) \
           and isinstance(target,
                          (cpptypes.free_function_type_t,
                           cpptypes.member_function_type_t,
                           cpptypes.member_variable_type_t)) \
           and is_same(source.base, target):
            return True

        if is_pointer(target) \
           and is_reference(source) \
           and isinstance(source.base,
                          (cpptypes.free_function_type_t,
                           cpptypes.member_function_type_t,
                           cpptypes.member_variable_type_t)) \
           and is_same(source.base, target.base):
            return True

        if is_pointer(target) \
           and isinstance(source,
                          (cpptypes.free_function_type_t,
                           cpptypes.member_function_type_t,
                           cpptypes.member_variable_type_t)) \
           and is_same(target.base, source):
            return True

    def __test_const_x_ref__to__x(self, source, target):
        if not is_reference(source) \
           or not is_const(source.base) \
           or not is_same(source.base.base, target):
            return False
        if is_fundamental(target):
            return True
        if is_enum(target):
            return True
        if isinstance(target, cpptypes.declarated_t):
            assert isinstance(target.declaration, class_declaration.class_t)
            if has_copy_constructor(target.declaration):
                return True  # we have copy constructor
        return False

    def __test_const_ref_x__to__y(self, source, target):
        if not is_reference(source) or not is_const(source.base):
            return False
        if is_fundamental(source.base.base) and is_fundamental(target):
            return True
        if is_convertible(source.base.base, cpptypes.int_t()) and \
                is_enum(target):
            return True
        if isinstance(target, cpptypes.declarated_t):
            assert isinstance(target.declaration, class_declaration.class_t)
            if has_copy_constructor(target.declaration):
                return True  # we have copy constructor
        return False

    def __test_ref_x__to__x(self, source, target):
        if not is_reference(source) or not is_same(source.base, target):
            return False
        if is_fundamental(target):
            return True
        if is_enum(target):
            return True
        if isinstance(target, cpptypes.declarated_t):
            assert isinstance(target.declaration, class_declaration.class_t)
            if has_copy_constructor(target.declaration):
                return True  # we have copy constructor
        return False

    def __test_ref_x__to__y(self, source, target):
        if not is_reference(source):
            return False
        if is_fundamental(source.base) and is_fundamental(target):
            return True
        if is_convertible(source.base, cpptypes.int_t()) and is_enum(target):
            return True
        if isinstance(target, cpptypes.declarated_t):
            assert isinstance(target.declaration, class_declaration.class_t)
            if has_copy_constructor(target.declaration):
                return True  # we have copy constructor
        return False

    def __test_fundamental__to__fundamental(self, source, target):
        if not is_fundamental(type_traits_utils.base_type(source)) or not \
                is_fundamental(type_traits_utils.base_type(target)):
            return False
        if is_void(type_traits_utils.base_type(source)) or \
                is_void(type_traits_utils.base_type(target)):
            return False
        if is_fundamental(source) and is_fundamental(target):
            return True
        if not is_pointer(source) and is_fundamental(target):
            return True
        if not is_pointer(source) and is_const(target) and\
                is_fundamental(target.base):
            return True
        if is_fundamental(source) \
           and is_reference(target) \
           and is_const(target.base) \
           and is_fundamental(target.base.base):
            return True  # X => const Y&
        return False

    def _is_both_declarated(self, x, y):
        return (
            isinstance(x, cpptypes.declarated_t) and
            isinstance(y, cpptypes.declarated_t))

    def __test_derived_to_based(self, source, target):
        derived = type_traits_utils.base_type(source)
        base = type_traits_utils.base_type(target)
        if not (
                isinstance(derived, cpptypes.declarated_t) and
                isinstance(derived.declaration, class_declaration.class_t)):
            return False
        if not (isinstance(base, cpptypes.declarated_t) and
                isinstance(base.declaration, class_declaration.class_t)):
            return False
        base = base.declaration
        derived = derived.declaration
        if not is_base_and_derived(base, derived):
            return False
        for b in derived.recursive_bases:
            if ((b.related_class is base) and b.access_type !=
                    class_declaration.ACCESS_TYPES.PRIVATE):
                break
        else:
            return False

        base = target
        derived = source
        # d => b
        if self._is_both_declarated(base, derived):
            return True
        # d* => b*
        if is_pointer(derived) and is_pointer(base) \
           and self._is_both_declarated(base.base, derived.base):
            return True
        # const d* => const b*
        if is_pointer(derived) and is_pointer(base) \
           and is_const(derived.base) and is_const(base.base) \
           and self._is_both_declarated(base.base.base, derived.base.base):
            return True
        # d* => const b*
        if is_pointer(derived) and is_pointer(base) \
           and is_const(derived.base)\
           and self._is_both_declarated(base.base.base, derived.base):
            return True

        # d& => b&
        if is_reference(derived) and is_reference(base) \
           and self._is_both_declarated(base.base, derived.base):
            return True
        # const d& => const b&
        if is_reference(derived) and is_reference(base) \
           and is_const(derived.base) and is_const(base.base) \
           and self._is_both_declarated(base.base.base, derived.base.base):
            return True
        # d& => const b&
        if is_reference(derived) and is_reference(base) \
           and is_const(derived.base) \
           and self._is_both_declarated(base.base.base, derived.base):
            return True
        return False

    def is_convertible(self):
        source = self.__source
        target = self.__target

        if self.__test_trivial(source, target):
            return True
        if is_array(source) or is_array(target):
            return False
        if self.__test_const_x_ref__to__x(source, target):
            return True
        if self.__test_const_ref_x__to__y(source, target):
            return True
        if self.__test_ref_x__to__x(source, target):
            return True
        if self.__test_ref_x__to__y(source, target):
            return True
        if self.__test_fundamental__to__fundamental(source, target):
            return True
        if self.__test_pointer_to_func_or_mv__to__func_or_mv(source, target):
            return True
        if self.__test_derived_to_based(source, target):
            return True

        if isinstance(source, cpptypes.declarated_t):
            if isinstance(source.declaration, enumeration.enumeration_t) \
               and is_fundamental(target) \
               and not is_void(target):
                return True  # enum could be converted to any integral type

            if isinstance(source.declaration, class_declaration.class_t):
                source_inst = source.declaration
                # class instance could be convertible to something else if it
                # has operator
                casting_operators = scopedef.find_all_declarations(
                    source_inst.declarations,
                    decl_type=calldef_members.casting_operator_t,
                    recursive=False)
                if casting_operators:
                    for operator in casting_operators:
                        if is_convertible(operator.return_type, target):
                            return True

        # may be target is class too, so in this case we should check whether
        # is has constructor from source
        if isinstance(target, cpptypes.declarated_t):
            if isinstance(target.declaration, class_declaration.class_t):
                constructors = scopedef.find_all_declarations(
                    target.declaration.declarations,
                    decl_type=calldef_members.constructor_t,
                    recursive=False)
                if constructors:
                    for constructor in constructors:
                        if 1 != len(constructor.arguments):
                            continue
                        # TODO: add test to check explicitness
                        if is_convertible(source,
                                          constructor.arguments[0].decl_type):
                            return True

        return False


def is_convertible(source, target):
    """returns True, if source could be converted to target, otherwise False"""
    return __is_convertible_t(source, target).is_convertible()


def __is_noncopyable_single(class_):
    """implementation details"""
    # It is not enough to check base classes, we should also to check
    # member variables.
    logger = utils.loggers.cxx_parser

    if has_copy_constructor(class_) \
       and has_public_constructor(class_) \
       and has_public_assign(class_) \
       and has_public_destructor(class_):
        msg = os.linesep.join([
            "__is_noncopyable_single - %s - COPYABLE:" % class_.decl_string,
            "    trivial copy constructor: yes",
            "    public constructor: yes",
            "    public assign: yes",
            "    public destructor: yes"])
        logger.debug(msg)
        return False
    if class_.find_noncopyable_vars():
        logger.debug(
            ("__is_noncopyable_single(TRUE) - %s - contains noncopyable " +
             "members") % class_.decl_string)
        return True
    else:
        logger.debug((
            "__is_noncopyable_single(FALSE) - %s - COPYABLE, because is " +
            "doesn't contains noncopyable members") % class_.decl_string)
        return False


def is_noncopyable(class_):
    """returns True, if class is noncopyable, False otherwise"""
    logger = utils.loggers.cxx_parser
    class_decl = class_traits.get_declaration(class_)

    true_header = "is_noncopyable(TRUE) - %s - " % class_.decl_string
    # false_header = "is_noncopyable(false) - %s - " % class_.decl_string

    if is_union(class_):
        return False

    if class_decl.is_abstract:
        logger.debug(true_header + "abstract client")
        return True

    # if class has public, user defined copy constructor, than this class is
    # copyable
    copy_ = class_decl.find_copy_constructor()
    if copy_ and copy_.access_type == 'public' and not copy_.is_artificial:
        return False

    for base_desc in class_decl.recursive_bases:
        assert isinstance(base_desc, class_declaration.hierarchy_info_t)

        if base_desc.related_class.decl_string in \
                ('::boost::noncopyable', '::boost::noncopyable_::noncopyable'):
            logger.debug(true_header + "derives from boost::noncopyable")
            return True

        if not has_copy_constructor(base_desc.related_class):

            base_copy_ = base_desc.related_class.find_copy_constructor()

            if base_copy_:

                if base_copy_.access_type == 'private':
                    logger.debug(
                        true_header +
                        "there is private copy constructor")
                    return True
            else:
                if __is_noncopyable_single(base_desc.related_class):
                    logger.debug(
                        true_header +
                        "__is_noncopyable_single returned True")
                    return True

        if __is_noncopyable_single(base_desc.related_class):
            logger.debug(
                true_header +
                "__is_noncopyable_single returned True")
            return True

    if not has_copy_constructor(class_decl):
        logger.debug(true_header + "does not have trivial copy constructor")
        return True
    elif not has_public_constructor(class_decl):
        logger.debug(true_header + "does not have a public constructor")
        return True
    elif has_destructor(class_decl) and not has_public_destructor(class_decl):
        logger.debug(true_header + "has private destructor")
        return True
    else:
        return __is_noncopyable_single(class_decl)


def is_defined_in_xxx(xxx, cls):
    """
    small helper function, that checks whether the class `cls` is defined
    under `::xxx` namespace
    """
    if not cls.parent:
        return False

    if not isinstance(cls.parent, namespace.namespace_t):
        return False

    if xxx != cls.parent.name:
        return False

    xxx_ns = cls.parent
    if not xxx_ns.parent:
        return False

    if not isinstance(xxx_ns.parent, namespace.namespace_t):
        return False

    if '::' != xxx_ns.parent.name:
        return False

    global_ns = xxx_ns.parent
    return None is global_ns.parent


class impl_details(object):

    """implementation details"""
    @staticmethod
    def is_defined_in_xxx(xxx, cls):
        """implementation details"""
        if not cls.parent:
            return False

        if not isinstance(cls.parent, namespace.namespace_t):
            return False

        if xxx != cls.parent.name:
            return False

        xxx_ns = cls.parent
        if not xxx_ns.parent:
            return False

        if not isinstance(xxx_ns.parent, namespace.namespace_t):
            return False

        if '::' != xxx_ns.parent.name:
            return False

        global_ns = xxx_ns.parent
        return None is global_ns.parent

    @staticmethod
    def find_value_type(global_ns, value_type_str):
        """implementation details"""
        if not value_type_str.startswith('::'):
            value_type_str = '::' + value_type_str
        found = global_ns.decls(
            name=value_type_str,
            function=lambda decl: not isinstance(decl, calldef.calldef_t),
            allow_empty=True)
        if not found:
            no_global_ns_value_type_str = value_type_str[2:]
            if no_global_ns_value_type_str in cpptypes.FUNDAMENTAL_TYPES:
                return cpptypes.FUNDAMENTAL_TYPES[no_global_ns_value_type_str]
            elif is_std_string(value_type_str):
                string_ = global_ns.typedef('::std::string')
                return remove_declarated(string_)
            elif is_std_wstring(value_type_str):
                string_ = global_ns.typedef('::std::wstring')
                return remove_declarated(string_)
            else:
                value_type_str = no_global_ns_value_type_str
                has_const = value_type_str.startswith('const ')
                if has_const:
                    value_type_str = value_type_str[len('const '):]
                has_pointer = value_type_str.endswith('*')
                if has_pointer:
                    value_type_str = value_type_str[:-1]
                found = None
                if has_const or has_pointer:
                    found = impl_details.find_value_type(
                        global_ns,
                        value_type_str)
                if not found:
                    return None
                else:
                    if isinstance(found, class_declaration.class_types):
                        found = cpptypes.declarated_t(found)
                    if has_const:
                        found = cpptypes.const_t(found)
                    if has_pointer:
                        found = cpptypes.pointer_t(found)
                    return found
        if len(found) == 1:
            return found[0]
        else:
            return None


class internal_type_traits(object):

    """small convenience class, which provides access to internal types"""
    # TODO: add exists function
    @staticmethod
    def get_by_name(type_, name):
        if class_traits.is_my_case(type_):
            cls = class_traits.declaration_class(type_)
            return remove_declarated(
                cls.typedef(name, recursive=False).decl_type)
        elif class_declaration_traits.is_my_case(type_):
            cls = class_declaration_traits.get_declaration(type_)
            value_type_str = templates.args(cls.name)[0]
            ref = impl_details.find_value_type(cls.top_parent, value_type_str)
            if ref:
                return ref
            else:
                raise RuntimeError((
                    "Unable to find reference to internal " +
                    "type '%s' in type '%s'.") % (name, cls.decl_string))
        else:
            raise RuntimeError((
                "Unable to find reference to internal type '%s' in type '%s'.")
                % (name, type_.decl_string))


class smart_pointer_traits(object):

    """implements functionality, needed for convenient work with
    smart pointers"""

    @staticmethod
    def is_smart_pointer(type_):
        """returns True, if type represents instantiation of
        `boost::shared_ptr` or `std::shared_ptr`, False otherwise"""
        type_ = type_traits_utils.remove_alias(type_)
        type_ = remove_cv(type_)
        type_ = remove_declarated(type_)
        if not isinstance(type_,
                          (class_declaration.class_declaration_t,
                           class_declaration.class_t)):
            return False
        if not (impl_details.is_defined_in_xxx('boost', type_) or
                impl_details.is_defined_in_xxx('std', type_)):
            return False
        return type_.decl_string.startswith('::boost::shared_ptr<') or \
            type_.decl_string.startswith('::std::shared_ptr<')

    @staticmethod
    def value_type(type_):
        """returns reference to `boost::shared_ptr` \
        or `std::shared_ptr` value type"""
        if not smart_pointer_traits.is_smart_pointer(type_):
            raise TypeError(
                'Type "%s" is not an instantiation of \
                boost::shared_ptr or std::shared_ptr' %
                type_.decl_string)
        return internal_type_traits.get_by_name(type_, "value_type")


class auto_ptr_traits(object):

    """implements functionality, needed for convenient work with
    `std::auto_ptr` pointers"""

    @staticmethod
    def is_smart_pointer(type_):
        """returns True, if type represents instantiation of
        `boost::shared_ptr`, False otherwise"""
        type_ = type_traits_utils.remove_alias(type_)
        type_ = remove_cv(type_)
        type_ = remove_declarated(type_)
        if not isinstance(type_,
                          (class_declaration.class_declaration_t,
                           class_declaration.class_t)):
            return False
        if not impl_details.is_defined_in_xxx('std', type_):
            return False
        return type_.decl_string.startswith('::std::auto_ptr<')

    @staticmethod
    def value_type(type_):
        """returns reference to `boost::shared_ptr` value type"""
        if not auto_ptr_traits.is_smart_pointer(type_):
            raise TypeError(
                'Type "%s" is not instantiation of std::auto_ptr' %
                type_.decl_string)
        return internal_type_traits.get_by_name(type_, "element_type")

string_equivalences = [
    ('::std::basic_string<char,std::char_traits<char>,' +
        'std::allocator<char> >'),
    ('::std::basic_string<char, std::char_traits<char>, ' +
        'std::allocator<char> >'),
    '::std::basic_string<char>', '::std::string']

wstring_equivalences = [
    ('::std::basic_string<wchar_t,std::char_traits<wchar_t>,' +
        'std::allocator<wchar_t> >'),
    ('::std::basic_string<wchar_t, std::char_traits<wchar_t>, ' +
        'std::allocator<wchar_t> >'),
    '::std::basic_string<wchar_t>', '::std::wstring']

ostream_equivalences = [
    '::std::basic_ostream<char, std::char_traits<char> >',
    '::std::basic_ostream<char,std::char_traits<char> >',
    '::std::basic_ostream<char>', '::std::ostream']

wostream_equivalences = [
    '::std::basic_ostream<wchar_t, std::char_traits<wchar_t> >',
    '::std::basic_ostream<wchar_t,std::char_traits<wchar_t> >',
    '::std::basic_ostream<wchar_t>', '::std::wostream']


def is_std_string(type_):
    """
    Returns True, if type represents C++ `std::string`, False otherwise.

    """

    if utils.is_str(type_):
        return type_ in string_equivalences
    else:
        type_ = type_traits_utils.remove_alias(type_)
        return remove_cv(type_).decl_string in string_equivalences


def is_std_wstring(type_):
    """
    Returns True, if type represents C++ `std::wstring`, False otherwise.

    """

    if utils.is_str(type_):
        return type_ in wstring_equivalences
    else:
        type_ = type_traits_utils.remove_alias(type_)
        return remove_cv(type_).decl_string in wstring_equivalences


def is_std_ostream(type_):
    """
    Returns True, if type represents C++ std::ostream, False otherwise.

    """

    if utils.is_str(type_):
        return type_ in ostream_equivalences
    else:
        type_ = type_traits_utils.remove_alias(type_)
        return remove_cv(type_).decl_string in ostream_equivalences


def is_std_wostream(type_):
    """
    Returns True, if type represents C++ std::wostream, False otherwise.

    """

    if utils.is_str(type_):
        return type_ in wostream_equivalences
    else:
        type_ = type_traits_utils.remove_alias(type_)
        return remove_cv(type_).decl_string in wostream_equivalences


def is_copy_constructor(args, parent):
        """
        Returns True if described declaration is copy constructor,
        otherwise False.

        """

        # A copy constructor has only one argument
        if len(args) != 1:
            return False

        # We have only one argument, get it
        arg = args[0]

        if not isinstance(arg.decl_type, cpptypes.compound_t):
            # An argument of type declarated_t (a typedef) could be passed to
            # the constructor; and it could be a reference.
            # But in c++ you can NOT write :
            #    "typedef class MyClass { MyClass(const MyClass & arg) {} }"
            # If the argument is a typedef, this is not a copy constructor.
            # See the hierarchy of declarated_t and coumpound_t. They both
            # inherit from type_t but are not related so we can discriminate
            # between them.
            return False

        # The argument needs to be passed by reference in a copy constructor
        if not is_reference(arg.decl_type):
            return False

        # The argument needs to be const for a copy constructor
        if not is_const(arg.decl_type.base):
            return False

        un_aliased = type_traits_utils.remove_alias(arg.decl_type.base)
        # un_aliased now refers to const_t instance
        if not isinstance(un_aliased.base, cpptypes.declarated_t):
            # We are looking for a declaration
            # If "class MyClass { MyClass(const int & arg) {} }" is used,
            # this is not copy constructor, so we return False here.
            # -> un_aliased.base == cpptypes.int_t (!= cpptypes.declarated_t)
            return False

        # Final check: compare the parent (the class declaration for example)
        # with the declaration of the type passed as argument.
        return id(un_aliased.base.declaration) == id(parent)
