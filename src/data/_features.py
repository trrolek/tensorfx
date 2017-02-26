# Copyright 2016 TensorLab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.

# _features.py
# Implementation of FeatureSet and related class.

import enum
import tensorflow as tf
import yaml


class FeatureType(enum.Enum):
  """Defines the type of Feature instances.
  """
  identity = 'identity'
  target = 'target'


class Feature(object):
  """Defines a named feature within a FeatureSet.
  """
  def __init__(self, name, type, fields, transform=None):
    """Initializes a Feature with its name and source fields.

    Arguments:
      name: the name of the feature.
      type: the type of the feature.
      fields: the names of the fields making up this feature.
      transform: transform configuration to produce the feature.
    """
    if transform is None:
      transform = {}

    self._name = name
    self._type = type
    self._fields = fields
    self._transform = transform

  @classmethod
  def identity(cls, name, field):
    """Creates a feature representing an un-transformed schema field.

    Arguments:
      name: the name of the feature.
      field: the name of the field.
    Returns:
      An instance of a Feature.
    """
    return cls(name, FeatureType.identity, [field])

  @classmethod
  def target(cls, name, field):
    """Creates a feature representing the target value.
    
    Arguments:
      name: the name of the feature.
      field: the name of the field.
    Returns:
      An instance of a Feature.
    """
    return cls(name, FeatureType.target, [field])

  @property
  def name(self):
    """Retrieves the name of the feature.
    """
    return self._name
  
  @property
  def field(self):
    """Retrieves the field making up the feature if the feature is based on a single field.
    """
    if len(self._fields) == 1:
      return self._fields[0]
    return None
  
  @property
  def fields(self):
    """Retrieves the fields making up the feature.
    """
    return self._fields
  
  @property
  def type(self):
    """Retrieves the type of the feature.
    """
    return self._type
  
  @property
  def transform(self):
    """Retrieves the transform configuration to produce the feature.
    """
    return self._transform


class FeatureSet(object):
  """Represents the set of features consumed by a model during training and prediction.

  A FeatureSet contains a set of named features. Features are derived from input fields specified
  in a schema and constructed using a transformation.
  """
  def __init__(self, features):
    """Initializes a FeatureSet from its specified set of features.

    Arguments:
      features: the list of features within a FeatureSet.
    """
    self._features = features
    self._features_map = dict(map(lambda f: (f.name, f), features))

  @staticmethod
  def create(*args):
    """Creates a FeatureSet from a set of features.

    Arguments:
      args: a list or sequence of features defining the FeatureSet.
    Returns:
      A FeatureSet instance.
    """
    if not len(args):
      raise ValueError('One or more features must be specified.')

    if type(args[0]) == list:
      return FeatureSet(args[0])
    else:
      return FeatureSet(list(args))

  @staticmethod
  def parse(spec):
    """Parses a FeatureSet from a YAML specification.

    Arguments:
      spec: The feature specification to parse.
    Returns:
      A FeatureSet instance.
    """
    if isinstance(spec, FeatureSet):
      return spec

    spec = yaml.safe_load(spec)

    features = []
    for f in spec['features']:
      name = f['name']
      fields = f.get('fields', name)
      feature_type = FeatureType[f.get('type', 'identity')]
      transform = f.get('transform', None)

      if type(fields) is str:
        fields = map(lambda n: n.strip(), fields.split(','))

      feature = Feature(name, feature_type, fields, transform)
      features.append(feature)

    return FeatureSet(features)

  def transform_instances(self, instances, schema, metadata):
    """Transforms input instances to create features.

    Arguments:
      instances: dictionary of tensors key'ed from schema field names to values.
      schema: the associated schema describing the instances.
      metadata: the associated metadata from analyzing the data.
    Returns:
      A dictionary of tensors key'ed by feature names
    """
    features = {}

    field_list = []
    for feature in self._features:
      if feature.type == FeatureType.target:
        features['targets'] = tf.identity(instances[feature.field], name='target')
      else:
        field_list.append(instances[feature.field])

    features['features'] = tf.transpose(tf.stack(field_list), name='features')

    return features

  def __getitem__(self, index):
    """Retrives the specified Feature by name.

    Arguments:
      index: the name of the feature.
    Returns:
      The SchemaField if it exists; None otherwise.
    """
    return self._features_map.get(index, None)

  def __len__(self):
    """Retrieves the number of Features defined.
    """
    return len(self._features)

  def __iter__(self):
    """Creates an iterator over the features in the FeatureSet.
    """
    for feature in self._features:
      yield feature