/*
 * =============================================================
 *   SNAKE GAME - Terminal Edition
 *   Viết bằng C++ thuần, chạy trên macOS/Linux terminal
 *
 *   Điều khiển:
 *     W / ↑  : Lên
 *     S / ↓  : Xuống
 *     A / ←  : Trái
 *     D / →  : Phải
 *     Q       : Thoát
 * =============================================================
 */

#include <iostream>
#include <deque>
#include <cstdlib>
#include <ctime>
#include <csignal>
#include <termios.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

// ─── Constants ───────────────────────────────────────────────
static const int  WIDTH       = 40;
static const int  HEIGHT      = 20;
static const int  FRAME_US    = 120000; // microseconds per frame (~8 fps)
static const char SNAKE_HEAD  = '@';
static const char SNAKE_BODY  = 'O';
static const char FOOD_CHAR   = '*';
static const char WALL_H      = '-';
static const char WALL_V      = '|';
static const char CORNER      = '+';
static const char EMPTY       = ' ';

// ─── Direction ───────────────────────────────────────────────
enum Direction { UP, DOWN, LEFT, RIGHT };

// ─── Point ───────────────────────────────────────────────────
struct Point {
    int x, y;
    bool operator==(const Point& o) const { return x == o.x && y == o.y; }
};

// ─── Terminal raw mode helpers ────────────────────────────────
static struct termios g_oldTerm;

void enableRawMode() {
    tcgetattr(STDIN_FILENO, &g_oldTerm);
    struct termios raw = g_oldTerm;
    raw.c_lflag &= ~(ECHO | ICANON);
    raw.c_cc[VMIN]  = 0;
    raw.c_cc[VTIME] = 0;
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw);
}

void disableRawMode() {
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &g_oldTerm);
}

void clearScreen() {
    std::cout << "\033[2J\033[H";
}

void hideCursor() { std::cout << "\033[?25l"; }
void showCursor() { std::cout << "\033[?25h"; }

void moveCursor(int row, int col) {
    std::cout << "\033[" << row << ";" << col << "H";
}

// ─── Keyboard (non-blocking) ──────────────────────────────────
int readKey() {
    unsigned char c = 0;
    if (read(STDIN_FILENO, &c, 1) != 1) return -1;

    if (c == '\033') {
        unsigned char seq[2];
        if (read(STDIN_FILENO, &seq[0], 1) != 1) return '\033';
        if (read(STDIN_FILENO, &seq[1], 1) != 1) return '\033';
        if (seq[0] == '[') {
            switch (seq[1]) {
                case 'A': return 'w';
                case 'B': return 's';
                case 'C': return 'd';
                case 'D': return 'a';
            }
        }
        return '\033';
    }
    return c;
}

// ─── Game State ───────────────────────────────────────────────
struct Game {
    std::deque<Point> snake;
    Direction         dir        = RIGHT;
    Direction         nextDir    = RIGHT;
    Point             food       = {0, 0};
    int               score      = 0;
    int               highScore  = 0;
    bool              running    = true;
    bool              paused     = false;

    // Grid: 0 = empty, 1 = snake, 2 = food
    char grid[HEIGHT][WIDTH];

    void init() {
        srand((unsigned)time(nullptr));
        snake.clear();
        snake.push_back({WIDTH / 2,     HEIGHT / 2});
        snake.push_back({WIDTH / 2 - 1, HEIGHT / 2});
        snake.push_back({WIDTH / 2 - 2, HEIGHT / 2});
        dir     = RIGHT;
        nextDir = RIGHT;
        score   = 0;
        running = true;
        paused  = false;
        buildGrid();
        spawnFood();
    }

    void buildGrid() {
        for (int y = 0; y < HEIGHT; ++y)
            for (int x = 0; x < WIDTH; ++x)
                grid[y][x] = EMPTY;
        for (size_t i = 0; i < snake.size(); ++i)
            grid[snake[i].y][snake[i].x] = (i == 0) ? SNAKE_HEAD : SNAKE_BODY;
        grid[food.y][food.x] = FOOD_CHAR;
    }

    void spawnFood() {
        do {
            food.x = rand() % WIDTH;
            food.y = rand() % HEIGHT;
        } while (grid[food.y][food.x] != EMPTY);
        grid[food.y][food.x] = FOOD_CHAR;
    }

    void handleInput(int key) {
        switch (key) {
            case 'w': case 'W': if (dir != DOWN)  nextDir = UP;    break;
            case 's': case 'S': if (dir != UP)    nextDir = DOWN;  break;
            case 'a': case 'A': if (dir != RIGHT) nextDir = LEFT;  break;
            case 'd': case 'D': if (dir != LEFT)  nextDir = RIGHT; break;
            case 'p': case 'P': paused = !paused; break;
            case 'q': case 'Q': running = false;  break;
        }
    }

    bool update() {
        if (paused) return true;
        dir = nextDir;

        Point head = snake.front();
        switch (dir) {
            case UP:    head.y--; break;
            case DOWN:  head.y++; break;
            case LEFT:  head.x--; break;
            case RIGHT: head.x++; break;
        }

        // Wall collision
        if (head.x < 0 || head.x >= WIDTH || head.y < 0 || head.y >= HEIGHT)
            return false;

        // Self collision
        for (auto& p : snake)
            if (p == head) return false;

        bool ate = (head == food);
        snake.push_front(head);
        if (!ate) {
            snake.pop_back();
        } else {
            score += 10;
            if (score > highScore) highScore = score;
            buildGrid();
            spawnFood();
        }
        buildGrid();
        return true;
    }

    // ─── Render ───────────────────────────────────────────────
    void render() {
        // Buffer the whole frame as a string for flicker-free output
        std::string frame;
        frame.reserve(4096);

        // Move to top-left
        frame += "\033[H";

        // Top border
        frame += "\033[1;36m"; // cyan
        frame += CORNER;
        frame += std::string(WIDTH, WALL_H);
        frame += CORNER;
        frame += "\n";

        for (int y = 0; y < HEIGHT; ++y) {
            frame += WALL_V;
            for (int x = 0; x < WIDTH; ++x) {
                char c = grid[y][x];
                if (c == SNAKE_HEAD) {
                    frame += "\033[1;32m"; // bright green
                    frame += c;
                    frame += "\033[1;36m";
                } else if (c == SNAKE_BODY) {
                    frame += "\033[0;32m"; // green
                    frame += c;
                    frame += "\033[1;36m";
                } else if (c == FOOD_CHAR) {
                    frame += "\033[1;31m"; // bright red
                    frame += c;
                    frame += "\033[1;36m";
                } else {
                    frame += c;
                }
            }
            frame += WALL_V;
            frame += "\n";
        }

        // Bottom border
        frame += CORNER;
        frame += std::string(WIDTH, WALL_H);
        frame += CORNER;
        frame += "\n";
        frame += "\033[0m"; // reset

        // Stats bar
        frame += "\033[1;33m Score: \033[1;37m";
        frame += std::to_string(score);
        frame += "   \033[1;33mBest: \033[1;37m";
        frame += std::to_string(highScore);
        frame += "   \033[0;37mLength: ";
        frame += std::to_string(snake.size());
        frame += "   ";
        if (paused) frame += "\033[1;35m[PAUSED]";
        frame += "\033[0m\n";
        frame += "\033[0;90m W/A/S/D = Move  |  P = Pause  |  Q = Quit\033[0m\n";

        std::cout << frame;
        std::cout.flush();
    }

    void renderGameOver() {
        clearScreen();
        int cy = HEIGHT / 2 - 3;
        int cx = WIDTH  / 2 - 10;

        auto box = [&](const std::string& msg, int row, const std::string& color) {
            moveCursor(row, cx);
            std::cout << color << msg << "\033[0m";
        };

        box("╔══════════════════════╗", cy,     "\033[1;31m");
        box("║      GAME OVER!      ║", cy + 1, "\033[1;31m");
        box("║                      ║", cy + 2, "\033[1;31m");
        box("║  Score : " + std::to_string(score) +
            std::string(12 - std::to_string(score).size(), ' ') + "║",
            cy + 3, "\033[1;33m");
        box("║  Best  : " + std::to_string(highScore) +
            std::string(12 - std::to_string(highScore).size(), ' ') + "║",
            cy + 4, "\033[1;32m");
        box("║                      ║", cy + 5, "\033[1;31m");
        box("║  R = Restart  Q=Quit ║", cy + 6, "\033[0;37m");
        box("╚══════════════════════╝", cy + 7, "\033[1;31m");
        std::cout.flush();
    }
};

// ─── Cleanup on SIGINT ────────────────────────────────────────
void onSignal(int) {
    disableRawMode();
    showCursor();
    clearScreen();
    exit(0);
}

// ─── Main ─────────────────────────────────────────────────────
int main() {
    signal(SIGINT, onSignal);
    enableRawMode();
    hideCursor();
    clearScreen();

    Game game;
    game.init();

    while (true) {
        // Input
        int key = readKey();
        game.handleInput(key);

        // Update
        bool alive = game.update();

        if (!alive) {
            game.renderGameOver();

            // Wait for R or Q
            bool decided = false;
            while (!decided) {
                usleep(50000);
                int k = readKey();
                if (k == 'r' || k == 'R') {
                    game.init();
                    clearScreen();
                    decided = true;
                } else if (k == 'q' || k == 'Q') {
                    decided = true;
                    game.running = false;
                }
            }
            if (!game.running) break;
            continue;
        }

        if (!game.running) break;

        // Render
        game.render();

        usleep(FRAME_US);
    }

    disableRawMode();
    showCursor();
    clearScreen();
    std::cout << "\033[1;36mCảm ơn đã chơi Snake! 🐍\033[0m\n";
    std::cout << "Final score: \033[1;33m" << game.score
              << "\033[0m | Best: \033[1;32m" << game.highScore << "\033[0m\n";
    return 0;
}
