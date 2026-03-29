import { Injectable } from '@nestjs/common'
import * as crypto from 'crypto'

@Injectable()
export class ApiKeysService {
  generateApiKey() {
    const random = crypto.randomBytes(24).toString('hex')
    return `tk_live_${random}`
  }

  async createKey() {
    const userKey = this.generateApiKey()

    return {
      user_key: userKey,
    }
  }
}