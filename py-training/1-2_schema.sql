CREATE TABLE IF NOT EXISTS account_balances (
    account_id VARCHAR(64) PRIMARY KEY,
    balance_cents BIGINT NOT NULL DEFAULT 100000,
    version INT NOT NULL DEFAULT 1,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO account_balances (account_id, balance_cents, version)
VALUES ('acc_prod_001', 100000, 1)
ON CONFLICT (account_id) DO NOTHING;