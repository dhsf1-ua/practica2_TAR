#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

TARGET_X = 1.5
TARGET_Y = -1.5

APPROACH_X = 1.5
APPROACH_Y = -0.7

# Yaw para entrar en reversa: el robot da la espalda al parking, apunta a +y
REVERSE_YAW = math.pi / 2   # espalda hacia el fondo (-y), frente hacia afuera (+y)

XY_TOL  = 0.08
YAW_TOL = 0.04

LIN_SPEED = 0.12
ANG_SPEED = 0.35

(
    TURN_TO_APPROACH,   # 1. girar hacia el punto frente al hueco
    MOVE_TO_APPROACH,   # 2. avanzar hasta ese punto
    TURN_REVERSE,       # 3. girar 180 para dar la espalda al parking
    ENTER_REVERSE,      # 4. entrar en reversa (linear.x negativo)
    STOP                # 5. fin
) = range(5)

STATE_NAMES = ["TURN_TO_APPROACH", "MOVE_TO_APPROACH", "TURN_REVERSE",
               "ENTER_REVERSE", "STOP"]


def yaw_from_quaternion(x, y, z, w):
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


class ParkingNode(Node):

    def __init__(self):
        super().__init__('aparcamiento')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.sub = self.create_subscription(Odometry, '/odom', self.odom_cb, 10)

        self.x = self.y = self.yaw = 0.0
        self.state = TURN_TO_APPROACH

        self.create_timer(0.05, self.loop)
        self.get_logger().info('Nodo aparcamiento en reversa iniciado.')

    def odom_cb(self, msg: Odometry):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        self.yaw = yaw_from_quaternion(q.x, q.y, q.z, q.w)

    def dist(self, tx, ty):
        return math.hypot(tx - self.x, ty - self.y)

    def angle_to(self, tx, ty):
        return math.atan2(ty - self.y, tx - self.x)

    def angle_diff(self, target):
        d = target - self.yaw
        while d >  math.pi: d -= 2 * math.pi
        while d < -math.pi: d += 2 * math.pi
        return d

    def cmd(self, v=0.0, w=0.0):
        t = Twist()
        t.linear.x  = v
        t.angular.z = w
        return t

    def next_state(self, s):
        self.state = s
        self.get_logger().info(f'-> {STATE_NAMES[s]}')

    def loop(self):
        if self.state == TURN_TO_APPROACH:
            err = self.angle_diff(self.angle_to(APPROACH_X, APPROACH_Y))
            if abs(err) < YAW_TOL:
                self.pub.publish(self.cmd())
                self.next_state(MOVE_TO_APPROACH)
            else:
                self.pub.publish(self.cmd(w=ANG_SPEED * math.copysign(1, err)))

        elif self.state == MOVE_TO_APPROACH:
            if self.dist(APPROACH_X, APPROACH_Y) < XY_TOL:
                self.pub.publish(self.cmd())
                self.next_state(TURN_REVERSE)
            else:
                err = self.angle_diff(self.angle_to(APPROACH_X, APPROACH_Y))
                w = max(-ANG_SPEED, min(ANG_SPEED, 1.5 * err))
                self.pub.publish(self.cmd(v=LIN_SPEED, w=w))

        elif self.state == TURN_REVERSE:
            err = self.angle_diff(REVERSE_YAW)
            if abs(err) < YAW_TOL:
                self.pub.publish(self.cmd())
                self.next_state(ENTER_REVERSE)
            else:
                self.pub.publish(self.cmd(w=ANG_SPEED * math.copysign(1, err)))

        elif self.state == ENTER_REVERSE:
            if self.dist(TARGET_X, TARGET_Y) < XY_TOL:
                self.pub.publish(self.cmd())
                self.get_logger().info('Aparcamiento completado!')
                self.next_state(STOP)
            else:
                # En reversa: el heading opuesto al objetivo mantiene la recta
                reverse_heading = self.angle_to(TARGET_X, TARGET_Y) + math.pi
                while reverse_heading >  math.pi: reverse_heading -= 2 * math.pi
                while reverse_heading < -math.pi: reverse_heading += 2 * math.pi
                err = self.angle_diff(reverse_heading)
                w = max(-ANG_SPEED * 0.4, min(ANG_SPEED * 0.4, 1.5 * err))
                self.pub.publish(self.cmd(v=-LIN_SPEED, w=w))


def main(args=None):
    rclpy.init(args=args)
    node = ParkingNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.pub.publish(node.cmd())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()