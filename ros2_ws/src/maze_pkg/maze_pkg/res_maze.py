#!/usr/bin/env python3

import math

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class MazeResolver(Node):

    def __init__(self):
        super().__init__('res_maze')

        self.declare_parameter('desired_wall_distance', 0.45)
        self.declare_parameter('front_clearance', 0.55)
        self.declare_parameter('right_open_threshold', 1.25)
        self.declare_parameter('wall_detect_threshold', 0.90)
        self.declare_parameter('forward_speed', 0.17)
        self.declare_parameter('turn_speed', 0.80)
        self.declare_parameter('turning_forward_speed', 0.09)
        self.declare_parameter('turn_tolerance', 0.12)
        self.declare_parameter('post_turn_cooldown', 0.8)
        self.declare_parameter('exit_x_min', -5.8)
        self.declare_parameter('exit_x_max', -3.0)
        self.declare_parameter('exit_y_threshold', 10.1)

        self.desired_wall_distance = self.get_parameter(
            'desired_wall_distance').get_parameter_value().double_value
        self.front_clearance = self.get_parameter(
            'front_clearance').get_parameter_value().double_value
        self.right_open_threshold = self.get_parameter(
            'right_open_threshold').get_parameter_value().double_value
        self.wall_detect_threshold = self.get_parameter(
            'wall_detect_threshold').get_parameter_value().double_value
        self.forward_speed = self.get_parameter(
            'forward_speed').get_parameter_value().double_value
        self.turn_speed = self.get_parameter(
            'turn_speed').get_parameter_value().double_value
        self.turning_forward_speed = self.get_parameter(
            'turning_forward_speed').get_parameter_value().double_value
        self.turn_tolerance = self.get_parameter(
            'turn_tolerance').get_parameter_value().double_value
        self.post_turn_cooldown = self.get_parameter(
            'post_turn_cooldown').get_parameter_value().double_value
        self.exit_x_min = self.get_parameter(
            'exit_x_min').get_parameter_value().double_value
        self.exit_x_max = self.get_parameter(
            'exit_x_max').get_parameter_value().double_value
        self.exit_y_threshold = self.get_parameter(
            'exit_y_threshold').get_parameter_value().double_value

        self.latest_scan = None
        self.position = None
        self.yaw = None
        self.finished = False
        self.last_state = None
        self.turn_target_yaw = None
        self.turn_direction = 0.0
        self.turn_label = None
        self.turn_cooldown_until_ns = 0
        self.had_close_right_wall = False

        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', QoSProfile(depth=10))
        self.scan_sub = self.create_subscription(
            LaserScan,
            'scan',
            self.scan_callback,
            qos_profile_sensor_data,
        )
        self.odom_sub = self.create_subscription(
            Odometry,
            'odom',
            self.odom_callback,
            10,
        )
        self.timer = self.create_timer(0.1, self.control_loop)

        self.get_logger().info('Nodo res_maze activo. Resolviendo maze_1 con seguidor de pared derecha.')

    def scan_callback(self, msg):
        self.latest_scan = msg

    def odom_callback(self, msg):
        position = msg.pose.pose.position
        self.position = (position.x, position.y)
        orientation = msg.pose.pose.orientation
        self.yaw = self.quaternion_to_yaw(
            orientation.x,
            orientation.y,
            orientation.z,
            orientation.w,
        )

    def control_loop(self):
        if self.finished:
            self.stop_robot()
            return

        if self.latest_scan is None or self.yaw is None:
            return

        if self.has_reached_exit():
            self.finished = True
            self.stop_robot()
            x, y = self.position
            self.get_logger().info(
                f'Salida detectada en ({x:.2f}, {y:.2f}). El robot se detiene.')
            return

        front = self.get_sector_min_distance(-20.0, 20.0)
        right = self.get_sector_min_distance(-110.0, -70.0)
        front_right = self.get_sector_min_distance(-75.0, -20.0)
        now_ns = self.get_clock().now().nanoseconds
        close_right_wall = (
            right < self.wall_detect_threshold
            or front_right < self.wall_detect_threshold
        )

        if self.turn_target_yaw is not None:
            self.execute_turn(front, right, front_right)
            return

        if now_ns < self.turn_cooldown_until_ns:
            cmd = Twist()
            cmd.linear.x = self.turning_forward_speed
            self.publish_state(
                'salida_giro',
                front,
                right,
                front_right,
            )
            self.cmd_vel_pub.publish(cmd)
            return

        cmd = Twist()

        if front < self.front_clearance:
            self.start_turn(math.pi / 2.0, 'giro_izquierda', front, right, front_right)
            self.had_close_right_wall = close_right_wall
            return
        elif (
            self.had_close_right_wall and
            right > self.right_open_threshold
            and front_right > (self.right_open_threshold * 0.85)
            and front > (self.front_clearance + 0.20)
        ):
            self.start_turn(-math.pi / 2.0, 'giro_derecha', front, right, front_right)
            self.had_close_right_wall = False
            return
        else:
            if not close_right_wall:
                state = 'buscar_pared'
                cmd.linear.x = 0.15
                cmd.angular.z = -0.08
                if front < (self.front_clearance + 0.25):
                    cmd.linear.x = 0.06
                    cmd.angular.z = 0.35
            elif right > self.desired_wall_distance + 0.18:
                state = 'acercando_pared'
                cmd.linear.x = 0.14
                cmd.angular.z = -0.18
            else:
                state = 'seguir_pared'
                wall_error = self.desired_wall_distance - right
                heading_error = self.desired_wall_distance - front_right
                angular = (1.2 * wall_error) + (0.35 * heading_error)
                angular = max(min(angular, 0.55), -0.55)

                cmd.linear.x = self.forward_speed
                if front < self.front_clearance + 0.15:
                    cmd.linear.x = min(cmd.linear.x, 0.10)
                if abs(angular) > 0.40:
                    cmd.linear.x = min(cmd.linear.x, 0.08)

                cmd.angular.z = angular

        self.publish_state(state, front, right, front_right)
        self.had_close_right_wall = close_right_wall

        self.cmd_vel_pub.publish(cmd)

    def start_turn(self, delta_yaw, label, front, right, front_right):
        self.turn_target_yaw = self.normalize_angle(self.yaw + delta_yaw)
        self.turn_direction = 1.0 if delta_yaw > 0.0 else -1.0
        self.turn_label = label
        self.publish_state(label, front, right, front_right)

    def execute_turn(self, front, right, front_right):
        angle_error = self.normalize_angle(self.turn_target_yaw - self.yaw)

        if abs(angle_error) < self.turn_tolerance:
            self.turn_target_yaw = None
            self.turn_direction = 0.0
            self.turn_label = None
            cooldown_ns = int(self.post_turn_cooldown * 1e9)
            self.turn_cooldown_until_ns = self.get_clock().now().nanoseconds + cooldown_ns
            self.stop_robot()
            return

        cmd = Twist()
        cmd.angular.z = self.turn_direction * self.turn_speed
        self.publish_state(self.turn_label, front, right, front_right)
        self.cmd_vel_pub.publish(cmd)

    def publish_state(self, state, front, right, front_right):
        if state != self.last_state:
            self.get_logger().info(
                f'Estado: {state} | front={front:.2f} m, right={right:.2f} m, front_right={front_right:.2f} m')
            self.last_state = state

    def has_reached_exit(self):
        if self.position is None:
            return False

        x, y = self.position
        return self.exit_x_min <= x <= self.exit_x_max and y >= self.exit_y_threshold

    def get_sector_min_distance(self, start_deg, end_deg):
        if self.latest_scan is None:
            return float('inf')

        scan = self.latest_scan
        start = math.radians(start_deg)
        end = math.radians(end_deg)
        distances = []

        for index, value in enumerate(scan.ranges):
            if not math.isfinite(value):
                continue
            if value < scan.range_min or value > scan.range_max:
                continue

            angle = self.normalize_angle(scan.angle_min + (index * scan.angle_increment))
            if self.angle_in_sector(angle, start, end):
                distances.append(value)

        if not distances:
            return scan.range_max

        return min(distances)

    @staticmethod
    def angle_in_sector(angle, start, end):
        start = MazeResolver.normalize_angle(start)
        end = MazeResolver.normalize_angle(end)

        if start <= end:
            return start <= angle <= end

        return angle >= start or angle <= end

    @staticmethod
    def normalize_angle(angle):
        return math.atan2(math.sin(angle), math.cos(angle))

    @staticmethod
    def quaternion_to_yaw(x, y, z, w):
        siny_cosp = 2.0 * ((w * z) + (x * y))
        cosy_cosp = 1.0 - 2.0 * ((y * y) + (z * z))
        return math.atan2(siny_cosp, cosy_cosp)

    def stop_robot(self):
        self.cmd_vel_pub.publish(Twist())


def main(args=None):
    rclpy.init(args=args)
    node = MazeResolver()

    try:
        rclpy.spin(node)
    finally:
        node.stop_robot()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
