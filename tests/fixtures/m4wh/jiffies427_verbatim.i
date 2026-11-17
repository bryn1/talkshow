typedef long __kernel_clock_t;
typedef __kernel_clock_t clock_t;
struct timespec64;
extern unsigned long timespec64_to_clock_unused(void);
extern clock_t jiffies_to_clock_t(unsigned long x);
static inline __attribute__((__gnu_inline__)) __attribute__((__unused__)) __attribute__((no_instrument_function)) clock_t jiffies_delta_to_clock_t(long delta)
{
 return jiffies_to_clock_t(({ __auto_type __UNIQUE_ID_x_56 = (0L); __auto_type __UNIQUE_ID_y_57 = (delta); do { extern void __compiletime_assert_58(void) __attribute__((__error__("max""(""0L"", ""delta"") signedness error"))); if (!(!(!(((((typeof(__UNIQUE_ID_x_56))(-1)) < ( typeof(__UNIQUE_ID_x_56))1) ? (2 + (__builtin_constant_p((long long)(__UNIQUE_ID_x_56) >= 0) && ((long long)(__UNIQUE_ID_x_56) >= 0))) : (1 + 2 * (sizeof(__UNIQUE_ID_x_56) < 4))) & ((((typeof(__UNIQUE_ID_y_57))(-1)) < ( typeof(__UNIQUE_ID_y_57))1) ? (2 + (__builtin_constant_p((long long)(__UNIQUE_ID_y_57) >= 0) && ((long long)(__UNIQUE_ID_y_57) >= 0))) : (1 + 2 * (sizeof(__UNIQUE_ID_y_57) < 4))))))) __compiletime_assert_58(); } while (0); ((__UNIQUE_ID_x_56) > (__UNIQUE_ID_y_57) ? (__UNIQUE_ID_x_56) : (__UNIQUE_ID_y_57)); }));
}
