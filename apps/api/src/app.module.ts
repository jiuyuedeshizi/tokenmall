import { Module } from '@nestjs/common'
import { ApiKeysModule } from './modules/api-keys/api-keys.module'
import { ProxyController } from './modules/proxy/proxy.controller'
import { WalletService } from './modules/wallet/wallet.service'

@Module({
  controllers: [ProxyController],
  providers: [WalletService],
  imports: [ApiKeysModule],
})

export class AppModule {}