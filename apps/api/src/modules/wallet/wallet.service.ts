import { Injectable } from '@nestjs/common'
import { Pool } from 'pg'

const pool = new Pool({
  connectionString: 'postgresql://postgres:postgres@localhost:5432/tokenmall',
})

@Injectable()
export class WalletService {
  async getBalance(userId: number) {
    const res = await pool.query(
      'SELECT balance FROM wallet_accounts WHERE user_id=$1',
      [userId],
    )

    return res.rows[0]?.balance || 0
  }

  async deduct(userId: number, amount: number) {
    await pool.query('BEGIN')

    try {
      const res = await pool.query(
        'SELECT balance FROM wallet_accounts WHERE user_id=$1 FOR UPDATE',
        [userId],
      )

      const balance = Number(res.rows[0]?.balance || 0)

      if (balance < amount) {
        throw new Error('余额不足')
      }

      await pool.query(
        'UPDATE wallet_accounts SET balance = balance - $1 WHERE user_id=$2',
        [amount, userId],
      )

      await pool.query(
        `INSERT INTO wallet_transactions (user_id, amount, type, description)
         VALUES ($1, $2, 'consume', 'AI调用扣费')`,
        [userId, -amount],
      )

      await pool.query('COMMIT')
    } catch (err) {
      await pool.query('ROLLBACK')
      throw err
    }
  }
}