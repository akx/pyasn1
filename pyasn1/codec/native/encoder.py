#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
from collections import OrderedDict

from pyasn1 import debug
from pyasn1 import error
from pyasn1.compat import _MISSING
from pyasn1.type import base
from pyasn1.type import char
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

__all__ = ['encode']

LOG = debug.registerLoggee(__name__, flags=debug.DEBUG_ENCODER)


class AbstractItemEncoder(object):
    def encode(self, value, encodeFun, **options):
        raise error.PyAsn1Error('Not implemented')


class BooleanEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return bool(value)


class IntegerEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return int(value)


class BitStringEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return str(value)


class OctetStringEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return value.asOctets()


class TextStringEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return str(value)


class NullEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return None


class ObjectIdentifierEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return str(value)


class RealEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return float(value)


class SetEncoder(AbstractItemEncoder):
    protoDict = dict

    def encode(self, value, encodeFun, **options):
        inconsistency = value.isInconsistent
        if inconsistency:
            raise inconsistency

        namedTypes = value.componentType
        substrate = self.protoDict()

        for idx, (key, subValue) in enumerate(value.items()):
            if namedTypes and namedTypes[idx].isOptional and not value[idx].isValue:
                continue
            substrate[key] = encodeFun(subValue, **options)
        return substrate


class SequenceEncoder(SetEncoder):
    protoDict = OrderedDict


class SequenceOfEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        inconsistency = value.isInconsistent
        if inconsistency:
            raise inconsistency
        return [encodeFun(x, **options) for x in value]


class ChoiceEncoder(SequenceEncoder):
    pass


class AnyEncoder(AbstractItemEncoder):
    def encode(self, value, encodeFun, **options):
        return value.asOctets()


TAG_MAP = {
    univ.Boolean.tagSet: BooleanEncoder(),
    univ.Integer.tagSet: IntegerEncoder(),
    univ.BitString.tagSet: BitStringEncoder(),
    univ.OctetString.tagSet: OctetStringEncoder(),
    univ.Null.tagSet: NullEncoder(),
    univ.ObjectIdentifier.tagSet: ObjectIdentifierEncoder(),
    univ.Enumerated.tagSet: IntegerEncoder(),
    univ.Real.tagSet: RealEncoder(),
    # Sequence & Set have same tags as SequenceOf & SetOf
    univ.SequenceOf.tagSet: SequenceOfEncoder(),
    univ.SetOf.tagSet: SequenceOfEncoder(),
    univ.Choice.tagSet: ChoiceEncoder(),
    # character string types
    char.UTF8String.tagSet: TextStringEncoder(),
    char.NumericString.tagSet: TextStringEncoder(),
    char.PrintableString.tagSet: TextStringEncoder(),
    char.TeletexString.tagSet: TextStringEncoder(),
    char.VideotexString.tagSet: TextStringEncoder(),
    char.IA5String.tagSet: TextStringEncoder(),
    char.GraphicString.tagSet: TextStringEncoder(),
    char.VisibleString.tagSet: TextStringEncoder(),
    char.GeneralString.tagSet: TextStringEncoder(),
    char.UniversalString.tagSet: TextStringEncoder(),
    char.BMPString.tagSet: TextStringEncoder(),
    # useful types
    useful.ObjectDescriptor.tagSet: OctetStringEncoder(),
    useful.GeneralizedTime.tagSet: OctetStringEncoder(),
    useful.UTCTime.tagSet: OctetStringEncoder()
}


# Put in ambiguous & non-ambiguous types for faster codec lookup
TYPE_MAP = {
    univ.Boolean.typeId: BooleanEncoder(),
    univ.Integer.typeId: IntegerEncoder(),
    univ.BitString.typeId: BitStringEncoder(),
    univ.OctetString.typeId: OctetStringEncoder(),
    univ.Null.typeId: NullEncoder(),
    univ.ObjectIdentifier.typeId: ObjectIdentifierEncoder(),
    univ.Enumerated.typeId: IntegerEncoder(),
    univ.Real.typeId: RealEncoder(),
    # Sequence & Set have same tags as SequenceOf & SetOf
    univ.Set.typeId: SetEncoder(),
    univ.SetOf.typeId: SequenceOfEncoder(),
    univ.Sequence.typeId: SequenceEncoder(),
    univ.SequenceOf.typeId: SequenceOfEncoder(),
    univ.Choice.typeId: ChoiceEncoder(),
    univ.Any.typeId: AnyEncoder(),
    # character string types
    char.UTF8String.typeId: OctetStringEncoder(),
    char.NumericString.typeId: OctetStringEncoder(),
    char.PrintableString.typeId: OctetStringEncoder(),
    char.TeletexString.typeId: OctetStringEncoder(),
    char.VideotexString.typeId: OctetStringEncoder(),
    char.IA5String.typeId: OctetStringEncoder(),
    char.GraphicString.typeId: OctetStringEncoder(),
    char.VisibleString.typeId: OctetStringEncoder(),
    char.GeneralString.typeId: OctetStringEncoder(),
    char.UniversalString.typeId: OctetStringEncoder(),
    char.BMPString.typeId: OctetStringEncoder(),
    # useful types
    useful.ObjectDescriptor.typeId: OctetStringEncoder(),
    useful.GeneralizedTime.typeId: OctetStringEncoder(),
    useful.UTCTime.typeId: OctetStringEncoder()
}

# deprecated aliases, https://github.com/pyasn1/pyasn1/issues/9
tagMap = TAG_MAP
typeMap = TYPE_MAP


class SingleItemEncoder(object):

    TAG_MAP = TAG_MAP
    TYPE_MAP = TYPE_MAP

    def __init__(self, tagMap=_MISSING, typeMap=_MISSING, **ignored):
        self._tagMap = tagMap if tagMap is not _MISSING else self.TAG_MAP
        self._typeMap = typeMap if typeMap is not _MISSING else self.TYPE_MAP

    def __call__(self, value, **options):
        if not isinstance(value, base.Asn1Item):
            raise error.PyAsn1Error(
                'value is not valid (should be an instance of an ASN.1 Item)')

        if LOG:
            debug.scope.push(type(value).__name__)
            LOG('encoder called for type %s '
                '<%s>' % (type(value).__name__, value.prettyPrint()))

        tagSet = value.tagSet

        try:
            concreteEncoder = self._typeMap[value.typeId]

        except KeyError:
            # use base type for codec lookup to recover untagged types
            baseTagSet = tag.TagSet(
                value.tagSet.baseTag, value.tagSet.baseTag)

            try:
                concreteEncoder = self._tagMap[baseTagSet]

            except KeyError:
                raise error.PyAsn1Error('No encoder for %s' % (value,))

        if LOG:
            LOG('using value codec %s chosen by '
                '%s' % (concreteEncoder.__class__.__name__, tagSet))

        pyObject = concreteEncoder.encode(value, self, **options)

        if LOG:
            LOG('encoder %s produced: '
                '%s' % (type(concreteEncoder).__name__, repr(pyObject)))
            debug.scope.pop()

        return pyObject


class Encoder(object):
    SINGLE_ITEM_ENCODER = SingleItemEncoder

    def __init__(self, **options):
        self._singleItemEncoder = self.SINGLE_ITEM_ENCODER(**options)

    def __call__(self, pyObject, asn1Spec=None, **options):
        return self._singleItemEncoder(
            pyObject, asn1Spec=asn1Spec, **options)


#: Turns ASN.1 object into a Python built-in type object(s).
#:
#: Takes any ASN.1 object (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative)
#: walks all its components recursively and produces a Python built-in type or a tree
#: of those.
#:
#: One exception is that instead of :py:class:`dict`, the :py:class:`OrderedDict`
#: is used to preserve ordering of the components in ASN.1 SEQUENCE.
#:
#: Parameters
#: ----------
#  asn1Value: any pyasn1 object (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative)
#:     pyasn1 object to encode (or a tree of them)
#:
#: Returns
#: -------
#: : :py:class:`object`
#:     Python built-in type instance (or a tree of them)
#:
#: Raises
#: ------
#: ~pyasn1.error.PyAsn1Error
#:     On encoding errors
#:
#: Examples
#: --------
#: Encode ASN.1 value object into native Python types
#:
#: .. code-block:: pycon
#:
#:    >>> seq = SequenceOf(componentType=Integer())
#:    >>> seq.extend([1, 2, 3])
#:    >>> encode(seq)
#:    [1, 2, 3]
#:
encode = SingleItemEncoder()
