cmake_minimum_required(VERSION 3.16)
project(TaiBaiUnlockService VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Windows specific settings
if(WIN32)
    add_definitions(-DUNICODE -D_UNICODE)
    add_definitions(-DWIN32_LEAN_AND_MEAN)
    add_definitions(-DNOMINMAX)
endif()

# Source files for service
set(SERVICE_SOURCES
    TaiBaiService.cpp
    DesktopCapture.cpp
    CommandHandler.cpp
)

set(HEADERS
    TaiBaiService.h
)

# Create service executable
add_executable(TaiBaiService ${SERVICE_SOURCES} ${HEADERS})

# Create helper executable (runs in user session)
add_executable(TaiBaiHelper TaiBaiHelper.cpp)

target_link_libraries(TaiBaiHelper
    user32
    gdi32
    gdiplus
    ole32
    d3d11
    dxgi
)

# Link libraries
target_link_libraries(TaiBaiService
    advapi32
    user32
    gdi32
    gdiplus
    wtsapi32
    userenv
    ole32
    d3d11
    dxgi
)

# Set subsystem to console for service
set_target_properties(TaiBaiService PROPERTIES
    WIN32_EXECUTABLE FALSE
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# Set properties for helper
set_target_properties(TaiBaiHelper PROPERTIES
    WIN32_EXECUTABLE FALSE
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# Install
install(TARGETS TaiBaiService
    RUNTIME DESTINATION bin
)

message(STATUS "Building TaiBai Unlock Service")
message(STATUS "Output directory: ${CMAKE_BINARY_DIR}/bin")
