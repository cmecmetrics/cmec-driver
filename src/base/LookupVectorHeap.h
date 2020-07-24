///////////////////////////////////////////////////////////////////////////////
///
///	\file    LookupVectorHeap.h
///	\author  Paul Ullrich
///	\version July 23, 2019
///

#ifndef _LOOKUPVECTORHEAP_H_
#define _LOOKUPVECTORHEAP_H_

#include <vector>
#include <map>

///////////////////////////////////////////////////////////////////////////////

template <
	typename LookupObject,
	typename StoredObject
>
class LookupVectorHeap {

public:
	///	<summary>
	///		Lookup table.
	///	</summary>
	typedef std::map<LookupObject, size_t> LookupTable;

	///	<summary>
	///		Pointer to StoredObject.
	///	</summary>
	typedef StoredObject * StoredObjectPtr;

	///	<summary>
	///		Pointer to StoredObject.
	///	</summary>
	typedef const StoredObject * ConstStoredObjectPtr;

	///	<summary>
	///		Vector of pointers to stored objects.
	///	</summary>
	typedef std::vector<StoredObject *> StoredObjectVector;

	///	<summary>
	///		Iterator.
	///	</summary>
	class iterator {
		public:
			typename LookupTable::iterator m_iter;
			LookupVectorHeap * m_pheap;

		public:
			iterator(
				typename LookupTable::iterator iter,
				LookupVectorHeap * pheap
			) :
				m_iter(iter),
				m_pheap(pheap)
			{ }

			iterator operator++() {
				m_iter++;
				return *this;
			}

			iterator operator++(int) {
				m_iter++;
				return *this;
			}

			const LookupObject & key() {
				return m_iter->first;
			}

			StoredObjectPtr operator*() {
				return (*m_pheap)[m_iter->second];
			}

			bool operator==(const iterator & iter) const {
				if ((m_iter == iter.m_iter) && (m_pheap == iter.m_pheap)) {
					return true;
				}
				return false;
			}

			bool operator!=(const iterator & iter) const {
					if ((m_iter != iter.m_iter) || (m_pheap != iter.m_pheap)) {
					return true;
				}
				return false;
			}
	};

	///	<summary>
	///		Constant iterator.
	///	</summary>
	class const_iterator {
		public:
			typename LookupTable::const_iterator m_iter;
			const LookupVectorHeap * m_pheap;

		public:
			const_iterator(
				typename LookupTable::const_iterator iter,
				const LookupVectorHeap * pheap
			) :
				m_iter(iter),
				m_pheap(pheap)
			{ }

			const_iterator operator++() {
				m_iter++;
				return *this;
			}

			const_iterator operator++(int) {
				m_iter++;
				return *this;
			}

			const LookupObject & key() {
				return m_iter->first;
			}

			ConstStoredObjectPtr operator*() {
				return (*m_pheap)[m_iter->second];
			}

			bool operator==(const const_iterator & iter) const {
				if ((m_iter == iter.m_iter) && (m_pheap == iter.m_pheap)) {
					return true;
				}
				return false;
			}

			bool operator!=(const const_iterator & iter) const {
					if ((m_iter != iter.m_iter) || (m_pheap != iter.m_pheap)) {
					return true;
				}
				return false;
			}
	};

public:
	///	<summary>
	///		Destructor.
	///	</summary>
	~LookupVectorHeap() {
		for (size_t s = 0; s < m_vecStoredObjects.size(); s++) {
			delete m_vecStoredObjects[s];
		}
	}

	///	<summary>
	///		Get this size of this LookupVector.
	///	</summary>
	size_t size() const {
		return m_vecStoredObjects.size();
	}

	///	<summary>
	///		Insert an object into this LookupVector.
	///	</summary>
	void insert(
		const LookupObject & key,
		StoredObject * value
	) {
		size_t sIndex = size();
		m_mapLookupTable.insert(
			std::pair<LookupObject, size_t>(key, sIndex));
		m_vecStoredObjects.push_back(value);
	}

	///	<summary>
	///		Perform a lookup by index.
	///	</summary>
	StoredObjectPtr operator[](size_t ix) {
		return m_vecStoredObjects[ix];
	}

	///	<summary>
	///		Perform a lookup by index.
	///	</summary>
	ConstStoredObjectPtr operator[](size_t ix) const {
		return m_vecStoredObjects[ix];
	}

	///	<summary>
	///		Perform a lookup by LookupObject.
	///	</summary>
	iterator find(const LookupObject & key) {
		typename LookupTable::iterator iter = m_mapLookupTable.find(key);
		if (iter == m_mapLookupTable.end()) {
			return end();
		} else {
			return iterator(iter, this);
		}
	}

	///	<summary>
	///		Perform a lookup by LookupObject.
	///	</summary>
	const_iterator find(const LookupObject & key) const {
		typename LookupTable::iterator iter = m_mapLookupTable.find(key);
		if (iter == m_mapLookupTable.end()) {
			return end();
		} else {
			return iterator(iter, this);
		}
	}

	///	<summary>
	///		Iterator to beginning of vector.
	///	</summary>
	iterator begin() {
		return iterator(m_mapLookupTable.begin(), this);
	}

	///	<summary>
	///		Const iterator to beginning of vector.
	///	</summary>
	const_iterator begin() const {
		return const_iterator(m_mapLookupTable.begin(), this);
	}

	///	<summary>
	///		Iterator to end of vector.
	///	</summary>
	iterator end() {
		return iterator(m_mapLookupTable.end(), this);
	}

	///	<summary>
	///		Const iterator to end of vector.
	///	</summary>
	const_iterator end() const {
		return const_iterator(m_mapLookupTable.end(), this);
	}

protected:
	///	<summary>
	///		Map from LookupObject to vector index.
	///	</summary>
	LookupTable m_mapLookupTable;

	///	<summary>
	///		Vector of pointers to StoredObjects.
	///	</summary>
	StoredObjectVector m_vecStoredObjects;
};

///////////////////////////////////////////////////////////////////////////////

#endif // _LOOKUPVECTORHEAP_H_

