/************************************************
 * @author puzzzzzzle
 * @email 2359173906@qq.com
 * @desc
 * @time 2023/1/21
 * @file std_log.h
 * @version
 * version        author            desc
 * 1.0            puzzzzzzle       create
 ************************************************/

#pragma once

#include <cerrno>
#include <chrono>
#include <cstdio>
#include <iomanip>
#include <iostream>
#include <atomic>

#include "stl_to_steam.h"
#ifdef STD_LOG_SYNC
#include <mutex>
namespace LogInit {
// log 同步锁
inline std::mutex& get_std_log_lock() {
  static std::mutex lock{};
  return lock;
}
}  // namespace LogInit
#endif
namespace LogInit {
// log 等级定义
enum class LogLevel : int {
  TRACE,
  DEBUG,
  INFO,
  WARNING,
  ERROR,
  FATAL,
};
inline std::string log_now_time() {
  time_t t = std::time(nullptr);
  char ch[64]{};
  strftime(ch, sizeof(ch), "%Y-%m-%d %H-%M-%S", localtime(&t));
  return ch;
}
// log计数
inline std::atomic_int& get_std_log_count() {
  static std::atomic_int count{};
  return count;
}
// 全局log等级
inline LogLevel& log_level() {
  static LogLevel level{LogLevel::TRACE};
  return level;
}
inline void set_log_level(LogLevel level) { log_level() = level; }
}  // namespace LogInit

// log 格式定义
#define LOG_FORMAT(level, msg)                                                 \
  "[" << LogInit::get_std_log_count().fetch_add(1) << "] [" << #level << "] [" \
      << LogInit::log_now_time() << "] "                                       \
      << "[" << msg << "] [" << __FILE__ << ":" << __LINE__ << "  "            \
      << __PRETTY_FUNCTION__ << "]" << std::endl;
// 同步锁定义
#ifdef STD_LOG_SYNC
#define LOG_SYNC_LOCK() \
  std::unique_lock<std::mutex> inner_log_lock(LogInit::get_std_log_lock());
#else
#define LOG_SYNC_LOCK()
#endif

// log 等级定义
#define STD_LOG_DEF(stream, level, msg)                                 \
  if ((int)::LogInit::LogLevel::level >= (int)::LogInit::log_level()) { \
    LOG_SYNC_LOCK()                                                     \
    stream << LOG_FORMAT(level, msg)                                    \
  }

// 输出到不同stream的log
#define STD_LOG(level, msg) STD_LOG_DEF(std::cout, level, msg)
#define ERR_LOG(level, msg) STD_LOG_DEF(std::cerr, level, msg)

// log定义
#define LOG_TRACE(msg) STD_LOG(TRACE, msg)
#define LOG_DEBUG(msg) STD_LOG(DEBUG, msg)
#define LOG_INFO(msg) STD_LOG(INFO, msg)
#define LOG_WARNING(msg) ERR_LOG(WARNING, msg)
#define LOG_ERROR(msg) ERR_LOG(ERROR, msg)
// 只是一个参考，调用errno检查错误
#define LOG_PERROR(msg) \
  ERR_LOG(ERROR, msg << "[ reason maybe  :  " << strerror(errno) << " ]")
#define LOG_FATAL(msg) ERR_LOG(FATAL, msg)
