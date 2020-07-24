///////////////////////////////////////////////////////////////////////////////
///
///	\file	MathHelper.h
///	\author  Paul Ullrich
///	\version July 24, 2019
///

#ifndef _MATHHELPER_H_
#define _MATHHELPER_H_

#include <cmath>
#include <limits>
#include <algorithm>

///////////////////////////////////////////////////////////////////////////////

///	<summary>
///		Calculate the maximum of two values.
///	</summary>
template <typename _T>
_T Max(_T x1, _T x2) {
	return (x1>x2)?(x1):(x2);
}

///	<summary>
///		Calculate the minimum of two values.
///	</summary>
template <typename _T>
_T Min(_T x1, _T x2) {
	return (x1<x2)?(x1):(x2);
}

///	<summary>
///		Calculate the sign of a value.
///	</summary>
template <typename _T>
_T Sign(_T x1) {
	return (x1 < static_cast<_T>(0))?(static_cast<_T>(-1)):(static_cast<_T>(1));
}

///	<summary>
///		Clamp a value to be within a given range.
///	</summary>
template <typename _T>
_T Clamp(_T y, _T x1, _T x2) {
	return (y>x2)?(x2):((y<x1)?(x1):(y));
}

///	<summary>
///		Calculate the integer square root.
///	</summary>
///	<remarks>
///		Source: Crenshaw, Jack.  Integer square roots.
///		http://www.embedded.com/98/9802fe2.htm
///	</remarks>
inline unsigned int ISqrt(unsigned int a) {
	unsigned int irem = 0;
	unsigned int iroot = 0;
	for (int i = 0; i < 16; i++) {
		iroot <<= 1;
		irem = ((irem << 2) + (a >> 30));
		a <<= 2;
		iroot++;
		if (iroot <= irem) {
			irem -= iroot;
			iroot++;
		} else {
			iroot--;
		}
	}
	return (static_cast<unsigned int>(iroot >> 1));
}

///	<summary>
///		Calculate the integer power of integers function.
///	</summary>
inline int IntPow(int d, unsigned int p) {
	if (p == 0) {
		return 1;
	}

	unsigned int q;

	int iPow = d;
	for (q = 1; q < p; q++) {
		iPow *= d;
	}
	return iPow;
}

///	<summary>
///		Calculate the integer power function.
///	</summary>
inline double IPow(double d, unsigned int p) {
	unsigned int q;

	double dPow = 1.0;

	for (q = 0; q < p; q++) {
		dPow *= d;
	}
	return dPow;
}

///	<summary>
///		Calculate the integer factorial function.
///	</summary>
inline unsigned int IFact(unsigned int p) {
	unsigned int q;
	unsigned int iFact = 1;

	for (q = 2; q <= p; q++) {
		iFact *= q;
	}

	return iFact;
}

///	<summary>
///		A namespace containing helper functions for floating point arithmatic.
///	</summary>
namespace fpa {

	///	<summary>
	///		Local version of frexp() that handles infinities specially.
	///		Code by Nemo (https://stackoverflow.com/questions/13940316/)
	///	</summary>
	template<typename T>
	T my_frexp(const T num, int *exp) {
		typedef std::numeric_limits<T> limits;

		// Treat +-infinity as +-(2^max_exponent).
		if (std::abs(num) > limits::max()) {
			*exp = limits::max_exponent + 1;
			return std::copysign(0.5, num);
		} else {
			return std::frexp(num, exp);
		}
	}

	///	<summary>
	///		Determine if two floating point numbers are almost equal.
	///	</summary>
	template<typename T>
	bool almost_equal(const T a, const T b, const unsigned ulps=4) {
		// Handle NaN.
   		if (std::isnan(a) || std::isnan(b)) {
   			return false;
		}

  		typedef std::numeric_limits<T> limits;

		// Handle very small and exactly equal values.
		if (std::abs(a-b) <= ulps * limits::denorm_min()) {
			return true;
		}

		// frexp() does the wrong thing for zero.  But if we get this far
		// and either number is zero, then the other is too big, so just
		// handle that now.
		if (a == 0 || b == 0) {
			return false;
		}

		// Break the numbers into significand and exponent, sorting them by
		// exponent.
		int min_exp, max_exp;
		T min_frac = my_frexp(a, &min_exp);
		T max_frac = my_frexp(b, &max_exp);
		if (min_exp > max_exp) {
			std::swap(min_frac, max_frac);
			std::swap(min_exp, max_exp);
		}

		// Convert the smaller to the scale of the larger by adjusting its
		// significand.
		const T scaled_min_frac = std::ldexp(min_frac, min_exp-max_exp);

		// Since the significands are now in the same scale, and the larger
		// is in the range [0.5, 1), 1 ulp is just epsilon/2.
		return std::abs(max_frac-scaled_min_frac) <= ulps * limits::epsilon() / 2;
	}
}

///////////////////////////////////////////////////////////////////////////////

#endif
