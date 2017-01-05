# Copyright 2014-2017 Insight Software Consortium.
# Copyright 2004-2009 Roman Yakovenko.
# Distributed under the Boost Software License, Version 1.0.
# See http://www.boost.org/LICENSE_1_0.txt

"""
defines class that describes C++ global and member variable declaration
"""

from . import declaration
from . import class_declaration


class variable_t(declaration.declaration_t):

    """describes C++ global and member variable declaration"""

    def __init__(
            self,
            name='',
            decl_type=None,
            type_qualifiers=None,
            value=None,
            bits=None,
            mangled=None):
        """creates class that describes C++ global or member variable"""
        declaration.declaration_t.__init__(self, name)
        self._decl_type = decl_type
        self._type_qualifiers = type_qualifiers
        self._value = value
        self._bits = bits
        self._byte_offset = 0
        self._mangled = mangled

    def _get__cmp__items(self):
        """implementation details"""
        return [self.decl_type, self.type_qualifiers, self.value]

    def __eq__(self, other):
        """implementation details"""
        if not declaration.declaration_t.__eq__(self, other):
            return False
        return self.decl_type == other.decl_type \
            and self.type_qualifiers == other.type_qualifiers \
            and self.value == other.value \
            and self.bits == other.bits

    def __hash__(self):
        return super.__hash__(self)

    @property
    def decl_type(self):
        """reference to the variable :class:`decl_type <type_t>`"""
        return self._decl_type

    @decl_type.setter
    def decl_type(self, decl_type):
        self._decl_type = decl_type

    @property
    def type_qualifiers(self):
        """reference to the :class:`type_qualifiers_t` instance"""
        return self._type_qualifiers

    @type_qualifiers.setter
    def type_qualifiers(self, type_qualifiers):
        self._type_qualifiers = type_qualifiers

    @property
    def value(self):
        """string, that contains the variable value"""
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    @property
    def bits(self):
        """integer, that contains information about how many bit takes
            bit field"""
        return self._bits

    @bits.setter
    def bits(self, bits):
        self._bits = bits

    @property
    def byte_offset(self):
        """integer, offset of the field from the beginning of class."""
        return self._byte_offset

    @byte_offset.setter
    def byte_offset(self, byte_offset):
        self._byte_offset = byte_offset

    @property
    def access_type(self):
        if not isinstance(self.parent, class_declaration.class_t):
            raise RuntimeError((
                "access_type functionality only available on member" +
                "variables and not on global variables"))
        return self.parent.find_out_member_access_type(self)

    @property
    def mangled(self):
        """
        Unique declaration name generated by the compiler.

        :return: the mangled name
        :rtype: str

        """

        return self.get_mangled_name()

    @mangled.setter
    def mangled(self, mangled):
        self._mangled = mangled

    def i_depend_on_them(self, recursive=True):
        return [class_declaration.dependency_info_t(self, self.decl_type)]

    def get_mangled_name(self):
        if not self._mangled and not self._demangled \
           and not isinstance(self.parent, class_declaration.class_t):
            return self.name
        else:
            return self._mangled
