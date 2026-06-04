/**
 * Phase 295: Scala Geospatial Engine — 함수형 지리공간 인덱스
 * Immutable KD-Tree, Range/KNN 쿼리, 함수형 컬렉션 기반.
 */
package com.sdacs.geospatial

case class Vec3(x: Double, y: Double, z: Double) {
  def +(other: Vec3): Vec3 = Vec3(x + other.x, y + other.y, z + other.z)
  def -(other: Vec3): Vec3 = Vec3(x - other.x, y - other.y, z - other.z)
  def *(s: Double): Vec3 = Vec3(x * s, y * s, z * s)
  def distanceTo(other: Vec3): Double =
    math.sqrt((x - other.x) * (x - other.x) + (y - other.y) * (y - other.y) + (z - other.z) * (z - other.z))
}

case class SpatialObject(id: String, position: Vec3, data: Map[String, Any] = Map.empty)

sealed trait KDTree {
  def insert(obj: SpatialObject): KDTree
  def rangeQuery(center: Vec3, radius: Double): List[SpatialObject]
  def knn(center: Vec3, k: Int): List[(SpatialObject, Double)]
  def size: Int
}

case object EmptyTree extends KDTree {
  def insert(obj: SpatialObject): KDTree = Leaf(obj)
  def rangeQuery(center: Vec3, radius: Double): List[SpatialObject] = Nil
  def knn(center: Vec3, k: Int): List[(SpatialObject, Double)] = Nil
  def size: Int = 0
}

case class Leaf(obj: SpatialObject) extends KDTree {
  def insert(newObj: SpatialObject): KDTree = {
    val node = Node(obj, EmptyTree, EmptyTree, 0)
    node.insert(newObj)
  }
  def rangeQuery(center: Vec3, radius: Double): List[SpatialObject] =
    if (obj.position.distanceTo(center) <= radius) List(obj) else Nil
  def knn(center: Vec3, k: Int): List[(SpatialObject, Double)] =
    List((obj, obj.position.distanceTo(center)))
  def size: Int = 1
}

case class Node(
  obj: SpatialObject,
  left: KDTree,
  right: KDTree,
  axis: Int
) extends KDTree {

  private def coord(pos: Vec3, ax: Int): Double = ax % 3 match {
    case 0 => pos.x
    case 1 => pos.y
    case 2 => pos.z
  }

  def insert(newObj: SpatialObject): KDTree = {
    if (coord(newObj.position, axis) < coord(obj.position, axis))
      Node(obj, left.insert(newObj), right, axis)
    else
      Node(obj, left, right.insert(newObj), axis)
  }

  def rangeQuery(center: Vec3, radius: Double): List[SpatialObject] = {
    var results: List[SpatialObject] = Nil
    if (obj.position.distanceTo(center) <= radius) results = obj :: results
    val diff = coord(center, axis) - coord(obj.position, axis)
    if (diff - radius <= 0) results = results ++ left.rangeQuery(center, radius)
    if (diff + radius >= 0) results = results ++ right.rangeQuery(center, radius)
    results
  }

  def knn(center: Vec3, k: Int): List[(SpatialObject, Double)] = {
    val all = collectAll()
    all.map(o => (o, o.position.distanceTo(center)))
      .sortBy(_._2)
      .take(k)
  }

  private def collectAll(): List[SpatialObject] = {
    obj :: left.rangeQuery(Vec3(0, 0, 0), Double.MaxValue) ++ right.rangeQuery(Vec3(0, 0, 0), Double.MaxValue)
  }

  def size: Int = 1 + left.size + right.size
}

class GeospatialEngine {
  private var tree: KDTree = EmptyTree
  private var objects: Map[String, SpatialObject] = Map.empty

  def insert(obj: SpatialObject): Unit = {
    objects = objects + (obj.id -> obj)
    tree = tree.insert(obj)
  }

  def queryRadius(center: Vec3, radius: Double): List[SpatialObject] =
    tree.rangeQuery(center, radius)

  def queryKNN(center: Vec3, k: Int): List[(SpatialObject, Double)] =
    tree.knn(center, k)

  def get(id: String): Option[SpatialObject] = objects.get(id)

  def summary: Map[String, Any] = Map(
    "totalObjects" -> objects.size,
    "treeSize" -> tree.size
  )
}
