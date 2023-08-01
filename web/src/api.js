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
  }
};
