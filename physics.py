import pygame
import random

# Window size
WIDTH, HEIGHT = 800, 600

# Ball properties
BALL_RADIUS = 20
SPEED = 3

class Ball:
    def __init__(self):
        self.x = random.randint(BALL_RADIUS, WIDTH - BALL_RADIUS)
        self.y = random.randint(BALL_RADIUS, HEIGHT - BALL_RADIUS)
        self.vx = random.choice([-SPEED, SPEED])
        self.vy = random.choice([-SPEED, SPEED])

    def move(self):
        self.x += self.vx
        self.y += self.vy

        if self.x - BALL_RADIUS < 0 or self.x + BALL_RADIUS > WIDTH:
            self.vx *= -1
        if self.y - BALL_RADIUS < 0 or self.y + BALL_RADIUS > HEIGHT:
            self.vy *= -1

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 255, 255), (self.x, self.y), BALL_RADIUS)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    balls = [Ball() for _ in range(10)]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((0, 0, 0))

        for ball in balls:
            ball.move()
            ball.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()