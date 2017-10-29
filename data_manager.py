# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from PIL import Image
import cv2
import numpy as np
import random

IMAGE_CAPACITY = 12288

OP_AND       = 0
OP_IN_COMMON = 1
OP_IGNORE    = 2


class DataManager(object):
  def __init__(self):
    pass


  def _load_image(self, index, hsv=True):
    file_name = "data/image{}.png".format(index)
    if hsv:
      # [HSV]
      img = cv2.imread(file_name) # opencv returns [BGR] image
      hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV) # Convert to HSV
      scale = np.array([1.0/180.0, 1.0/255.0, 1.0/255.0],
                       dtype=np.float32) # Scale to fit 0.0 ~ 1.0
      return hsv * scale
    else:
      # [RGB]
      img = np.array(Image.open(file_name), dtype=np.float32)
      return img * (1.0/255.0)

    
  def prepare(self):
    print("start filling image pool")

    self.images = []

    for i in range(IMAGE_CAPACITY):
      image = self._load_image(i)
      self.images.append(image)
      
    print("finish filling image pool")
    
    self._prepare_indices()

    
  def _prepare_indices(self):
    self.image_indices = list(range(IMAGE_CAPACITY))
    random.shuffle(self.image_indices)
    self.used_image_index = 0

    
  def _get_masked_image(self, image):
    masked_image = image.copy()
    shape = masked_image.shape
    
    h = shape[0]
    w = shape[1]

    h0 = np.random.randint(0,h)
    h1 = np.random.randint(0,h)

    w0 = np.random.randint(0,w)
    w1 = np.random.randint(0,w)

    if h0 <= h1:
      hmin = h0
      hmax = h1+1
    else:
      hmin = h1
      hmax = h0+1

    if w0 <= w1:
      wmin = w0
      wmax = w1+1
    else:
      wmin = w1
      wmax = w0+1

    masked_image[hmin:hmax,wmin:wmax,:] = 0.0
    return masked_image


  def _randint_excepting(self, high, excep):
    list = []
    for r in range(high):
      if r != excep:
        list.append(r)
    random.shuffle(list)
    return list[0]

  
  def _choose_indices(self, high, size):
    indices = list(range(high))
    random.shuffle(indices)
    ret = indices[:size]
    # result is not sorted
    return ret
  
  
  def _choose_op_triplet(self, op_type):
    param_sizes = [8, 8, 8, 3]
    
    param0    = [-1, -1, -1, -1] # input0
    param1    = [-1, -1, -1, -1] # input1
    param_out = [-1, -1, -1, -1] # output
    
    if op_type == OP_AND:
      taret_type0 = np.random.randint(4)
      taret_type1 = self._randint_excepting(4, taret_type0)
      
      param0[taret_type0] = np.random.randint(0, param_sizes[taret_type0])
      param1[taret_type1] = np.random.randint(0, param_sizes[taret_type1])
      
      param_out[taret_type0] = param0[taret_type0]
      param_out[taret_type1] = param1[taret_type1]
      
    elif op_type == OP_IN_COMMON:
      target_size0 = np.random.randint(1, 5) # 1,2,3,4
      target_types0 = self._choose_indices(4, target_size0) # not sorted
      common_target_type = target_types0[0]
      
      target_size1 = np.random.randint(1, 5) # 1,2,3,4
      target_types1 = self._choose_indices(4, target_size1) # not sorted
      if common_target_type not in target_types1:
        target_types1.append(common_target_type)

      for i in range(4):
        if i in target_types0:
          param0[i] = np.random.randint(param_sizes[i])
        if i in target_types1:
          if i == common_target_type:
            param1[i] = param0[i]
            param_out[i] = param0[i]
          elif param0[i] != -1:
            param1[i] = self._randint_excepting(param_sizes[i], param0[i])
          else:
            param1[i] = np.random.randint(param_sizes[i])

    elif op_type == OP_IGNORE:
      target_size0 = np.random.randint(2, 5) # 1,2,3,4
      target_types0 = self._choose_indices(4, target_size0) # not sorted
      ignore_target_type = target_types0[0]
        
      for i in range(4):
        if i in target_types0:
          param0[i] = np.random.randint(param_sizes[i])
        if i == ignore_target_type:
          param1[i] = param0[i]
        else:
          param_out[i] = param0[i]

    return param0, param1, param_out

  
  def get_op_training_batch(self, batch_size):
    ys0 = []
    ys1 = []
    xs = []
    ys = []
    hs = []
    
    for i in range(batch_size):
      op_type = np.random.randint(0,3)
      param0, param1, param_out = self._choose_op_triplet(op_type)
      y0 = self.get_labels(param0[0], param0[1], param0[2], param0[3])
      y1 = self.get_labels(param1[0], param1[1], param1[2], param1[3])
      y = self.get_labels(param_out[0], param_out[1], param_out[2], param_out[3])
      x = self.get_image(param_out[0], param_out[1], param_out[2], param_out[3])
      ys0.append(y0)
      ys1.append(y1)
      ys.append(y)
      xs.append(x)
      hs.append(op_type)
    return ys0, ys1, ys, xs, hs

      
  def get_labels(self, obj_color=-1, wall_color=-1, floor_color=-1, obj_id=-1):
    """ Get labels (float array with 51 values of 0.0 or 1.0) by specifing each elements. 
    If element is -1, it means that element (color or object type) is not specified.
    """
    
    labels = np.zeros(3+16*3, dtype=np.float32)

    if obj_color >= 0:
      labels[obj_color] = 1.0

    if wall_color >= 0:
      labels[16 + wall_color] = 1.0

    if floor_color >= 0:
      labels[32 + floor_color] = 1.0

    if obj_id >= 0:
      labels[48 + obj_id] = 1.0
    
    return labels

  
  def _index_to_labels(self, index):
    obj_color = index % 16
    
    index = index // 16
    wall_color = index % 16
    
    index = index // 16
    floor_color = index % 16

    index = index // 16
    obj_id = index % 3
    
    return self.get_labels(obj_color, wall_color, floor_color, obj_id)


  def choose_labels(self, y):
    """ retrieve label element from img2sym output. """
    label_indices = []
    for i,v in enumerate(y):
      if random.random() <= v:
        label_indices.append(i)

    obj_color = []
    wall_color = []
    floor_color = []
    obj_id = []

    for index in label_indices:
      if index < 16:
        obj_color.append(index)
      elif index < 32:
        wall_color.append(index-16)
      elif index < 48:
        floor_color.append(index-32)
      else:
        obj_id.append(index-48)        
    return (obj_color, wall_color, floor_color, obj_id)
  
    
  def next_batch(self, batch_size, use_labels=False):
    batch = []

    if use_labels:
      labels_batch = []
    
    for i in range(batch_size):
      index = self.image_indices[self.used_image_index]
      image = self.images[index]
      batch.append(image)

      if use_labels:
        labels = self._index_to_labels(index)
        labels_batch.append(labels)
      
      self.used_image_index += 1
      if self.used_image_index >= IMAGE_CAPACITY:
        self._prepare_indices()

    if use_labels:
      return (batch, labels_batch)
    else:
      return batch
  
  
  def next_masked_batch(self, batch_size):
    batch_org = []
    batch_masked = []
    
    for i in range(batch_size):
      index = self.image_indices[self.used_image_index]
      image = self.images[index]
      batch_org.append(image)
      masked_image = self._get_masked_image(image)
      batch_masked.append(masked_image)
      
      self.used_image_index += 1
      if self.used_image_index >= IMAGE_CAPACITY:
        self._prepare_indices()

    return batch_masked, batch_org

  
  def get_image(self, obj_color, wall_color, floor_color, obj_id):
    index = obj_color + wall_color * 16 + floor_color * 16 * 16 + obj_id * 16 * 16 * 16
    image = self.images[index]
    return image
