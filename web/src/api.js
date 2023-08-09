import axios from 'axios'

const client = axios.create({
  baseURL: process.env.NODE_ENV === 'production' ? undefined : 'http://localhost:2023'
})

export default {
  async getTimersData() {
    const response = await client.get('/sync')
    return response.data
  },
  async getFlagStoreStats() {
    const response = await client.get('/flagstore-stats')
    return response.data
  },
  async getExploitAnalytics() {
    const response = await client.get('/exploit-analytics')
    return response.data
  },
  async searchFlags(page, show, sort, query) {
    const response = await client.post('/search', {
      "page": page,
      "show": show,
      "sort": sort,
      "query": query
    })
    return response.data
  }
};
