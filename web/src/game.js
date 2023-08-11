import api from '@/api.js'

export const game = {
    async initialize() {
        this.flagFormat = (await api.getFlagFormat()).format
    }
}