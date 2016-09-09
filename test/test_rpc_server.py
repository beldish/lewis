import unittest

from . import assertRaisesNothing

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

from core.rpc_server import ExposedObject, ExposedObjectCollection, ZMQJSONRPCServer


class TestObject(object):
    def __init__(self):
        self.a = 10
        self.b = 20

        self.getTest = Mock()
        self.setTest = Mock()


class TestRPCObject(unittest.TestCase):
    def test_all_methods_exposed(self):
        rpc_object = ExposedObject(TestObject())

        expected_methods = [':api', 'a:get', 'a:set', 'b:get', 'b:set', 'getTest', 'setTest']
        self.assertEqual(len(rpc_object), len(expected_methods))

        for method in expected_methods:
            self.assertTrue(method in rpc_object)

    def test_select_methods_exposed(self):
        rpc_object = ExposedObject(TestObject(), ('a', 'getTest'))

        expected_methods = [':api', 'a:get', 'a:set', 'getTest']
        self.assertEqual(len(rpc_object), len(expected_methods))

        for method in expected_methods:
            self.assertTrue(method in rpc_object)

    def test_invalid_method_raises(self):
        self.assertRaises(AttributeError, ExposedObject, TestObject(), ('nonExisting',))

    def test_attribute_wrapper_gets_value(self):
        obj = TestObject()
        obj.a = 233

        rpc_object = ExposedObject(obj)
        self.assertEqual(rpc_object['a:get'](), obj.a)

    def test_attribute_wrapper_sets_value(self):
        obj = TestObject()
        obj.a = 233

        rpc_object = ExposedObject(obj)

        self.assertEqual(obj.a, 233)
        rpc_object['a:set'](20)
        self.assertEqual(obj.a, 20)

    def test_attribute_wrapper_argument_number(self):
        rpc_object = ExposedObject(TestObject())

        self.assertRaises(TypeError, rpc_object['a:get'], 20)
        self.assertRaises(TypeError, rpc_object['a:set'])
        self.assertRaises(TypeError, rpc_object['a:set'], 40, 30)

    def test_method_wrapper_calls(self):
        obj = TestObject()
        rpc_object = ExposedObject(obj)

        rpc_object['getTest'](45, 56)

        obj.getTest.assert_called_with(45, 56)

    def test_get_api(self):
        obj = TestObject()
        rpc_object = ExposedObject(obj, ['a'])
        api = rpc_object.get_api()

        self.assertTrue('class' in api)
        self.assertEqual(api['class'], type(obj).__name__)

        self.assertTrue('methods' in api)
        self.assertEqual(set(api['methods']), {':api', 'a:set', 'a:get'})


class TestExposedObjectCollection(unittest.TestCase):
    def test_empty_initialization(self):
        exposed_objects = ExposedObjectCollection(named_objects={})
        self.assertEqual(set(exposed_objects), {':api', 'get_objects'})

        self.assertEqual(len(exposed_objects.get_objects()), 0)
        self.assertEqual(exposed_objects['get_objects'](), exposed_objects.get_objects())

    def test_api(self):
        exposed_objects = ExposedObjectCollection(named_objects={})

        api = exposed_objects[':api']()
        self.assertTrue('class' in api)
        self.assertEqual(api['class'], 'ExposedObjectCollection')
        self.assertTrue('methods' in api)
        self.assertEqual(set(api['methods']), {'get_objects', ':api'})

    def test_add_plain_object(self):
        exposed_objects = ExposedObjectCollection({})
        obj = TestObject()

        assertRaisesNothing(self, exposed_objects.add_object, obj, 'testObject')

        # There should be :api, get_objects, testObject:api, testObject.a:get, testObject.a:set,
        # testObject.b:get, testObject.b:set, testObject.getTest, testObject.setTest
        self.assertEqual(len(exposed_objects), 9)

        exposed_objects['testObject.getTest'](34, 55)
        obj.getTest.assert_called_once_with(34, 55)

    def test_add_exposed_object(self):
        exposed_objects = ExposedObjectCollection({})
        obj = TestObject()

        assertRaisesNothing(self, exposed_objects.add_object, ExposedObject(obj, ('setTest', 'getTest')), 'testObject')
        exposed_objects['testObject.getTest'](41, 11)
        obj.getTest.assert_called_once_with(41, 11)

    def test_nested_collections(self):
        obj = TestObject()
        exposed_objects = ExposedObjectCollection({'container': ExposedObjectCollection({'test': obj})})

        exposed_objects['container.test.getTest'](454, 43)
        obj.getTest.assert_called_once_with(454, 43)
