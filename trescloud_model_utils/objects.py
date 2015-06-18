from osv import fields, osv


class oop_utils(osv.osv_memory):
    _name = 'oop.utils'

    def supercall(self, klass, instance, method, ifAbsent=None):
        """
        Treats the object as super() and tried to get a method from it (the inherited method). If
          the method does not exist (as attribute) in the super class, a callable taking arbitrary
          arguments and returning the value in ifAbsent is returned.
        Such callable will be evaluated later (being a normal method or a subsidiary function).
        :param klass:
        :param instance:
        :param method:
        :param ifAbsent:
        :return:
        """
        return getattr(super(klass, instance), method, lambda *a, **kwa: ifAbsent)
oop_utils()