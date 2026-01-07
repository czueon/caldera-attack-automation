// victim.cpp
#include <windows.h>
#include <iostream>

int main() {
    std::cout << "===================================\n";
    std::cout << "  Clean Process Running\n";
    std::cout << "  PID: " << GetCurrentProcessId() << "\n";
    std::cout << "===================================\n\n";
    
    int counter = 0;
    while(true) {
        std::cout << "[" << counter++ << "] Normal operation...\n";
        Sleep(2000);
    }
    
    return 0;
}