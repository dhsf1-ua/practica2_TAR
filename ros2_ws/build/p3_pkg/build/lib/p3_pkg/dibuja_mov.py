import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
import matplotlib.pyplot as plt

class DibujaMov(Node):
    def __init__(self):
        super().__init__('dibuja_mov_node')
        self.subscription = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        self.x_data = []
        self.y_data = []
        self.get_logger().info('Registrador de trayectoria iniciado. Ctrl+C para ver el gráfico.')

    def odom_callback(self, msg):
        self.x_data.append(msg.pose.pose.position.x)
        self.y_data.append(msg.pose.pose.position.y)

    def graficar(self):
        plt.figure(figsize=(8, 6))
        plt.plot(self.x_data, self.y_data, label='Trayectoria Robot')
        plt.xlabel('Posición X (m)')
        plt.ylabel('Posición Y (m)')
        plt.title('Trayectoria del Turtlebot 3')
        plt.grid(True)
        plt.legend()
        plt.show()

def main():
    rclpy.init()
    nodo = DibujaMov()
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        nodo.get_logger().info('Generando gráfico...')
        nodo.graficar()
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()
