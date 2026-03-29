import { Controller, Post, Headers, Body } from '@nestjs/common'
import axios from 'axios'
import { WalletService } from '../wallet/wallet.service'

@Controller('proxy')
export class ProxyController {
  constructor(private walletService: WalletService) {}

  @Post('chat')
  async chat(@Headers('authorization') auth: string, @Body() body: any) {
    const key = auth?.replace('Bearer ', '')

    // 👉 TODO: 这里先写死 userId
    const userId = 1

    // 1️⃣ 检查余额
    const balance = await this.walletService.getBalance(userId)

    if (balance <= 0) {
      throw new Error('余额不足')
    }

    // 2️⃣ 调 LiteLLM
    const res = await axios.post(
      'http://localhost:4000/v1/chat/completions',
      body,
      {
        headers: {
          Authorization: 'Bearer sk-tokenmall-master',
        },
      },
    )

    // 3️⃣ 简单扣费（先写死价格）
    await this.walletService.deduct(userId, 0.01)

    return res.data
  }
}