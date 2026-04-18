// MongoDB initialization script
// Runs on first container startup

// Switch to tradebot database
db = db.getSiblingDB('tradebot');

// Create application user with read-write permissions
db.createUser({
    user: 'tradebot',
    pwd: 'tradebot123',
    roles: [
        { role: 'readWrite', db: 'tradebot' },
        { role: 'dbAdmin', db: 'tradebot' }
    ]
});

// Create collections with validation
db.createCollection('positions', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['ticker', 'strike', 'option_type', 'quantity', 'entry_price', 'status'],
            properties: {
                ticker: { bsonType: 'string', description: 'Stock ticker' },
                strike: { bsonType: 'number', description: 'Strike price' },
                option_type: { enum: ['CALL', 'PUT'], description: 'Option type' },
                quantity: { bsonType: 'int', minimum: 1 },
                entry_price: { bsonType: 'double', minimum: 0 },
                status: { enum: ['OPEN', 'CLOSED', 'CANCELLED'] },
                entry_time: { bsonType: 'date' },
                exit_time: { bsonType: 'date' },
                pnl: { bsonType: 'double' },
                broker: { bsonType: 'string' }
            }
        }
    }
});

db.createCollection('trades', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['ticker', 'action', 'quantity', 'price', 'timestamp'],
            properties: {
                ticker: { bsonType: 'string' },
                action: { enum: ['BTO', 'STC', 'BTC', 'STO'] },
                quantity: { bsonType: 'int', minimum: 1 },
                price: { bsonType: 'double', minimum: 0 },
                timestamp: { bsonType: 'date' },
                order_id: { bsonType: 'string' },
                broker: { bsonType: 'string' },
                status: { enum: ['PENDING', 'FILLED', 'REJECTED', 'CANCELLED'] }
            }
        }
    }
});

db.createCollection('alerts', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['ticker', 'alert_type', 'timestamp'],
            properties: {
                ticker: { bsonType: 'string' },
                alert_type: { enum: ['BTO', 'STC', 'BTC', 'STO'] },
                message: { bsonType: 'string' },
                timestamp: { bsonType: 'date' },
                source: { bsonType: 'string' },
                processed: { bsonType: 'bool' },
                confidence: { bsonType: 'double' }
            }
        }
    }
});

db.createCollection('settings', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['key'],
            properties: {
                key: { bsonType: 'string' },
                value: { bsonType: 'object' },
                category: { bsonType: 'string' },
                updated_at: { bsonType: 'date' }
            }
        }
    }
});

db.createCollection('profiles', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['discord_user_id', 'name'],
            properties: {
                discord_user_id: { bsonType: 'string' },
                name: { bsonType: 'string' },
                broker: { bsonType: 'string' },
                settings: { bsonType: 'object' },
                created_at: { bsonType: 'date' },
                last_active: { bsonType: 'date' }
            }
        }
    }
});

// Create indexes for performance
db.positions.createIndex({ ticker: 1, status: 1 });
db.positions.createIndex({ entry_time: -1 });
db.positions.createIndex({ status: 1, exit_time: 1 });

db.trades.createIndex({ ticker: 1, timestamp: -1 });
db.trades.createIndex({ order_id: 1 }, { unique: true });
db.trades.createIndex({ timestamp: -1 });

db.alerts.createIndex({ timestamp: -1 });
db.alerts.createIndex({ processed: 1, timestamp: -1 });
db.alerts.createIndex({ ticker: 1, alert_type: 1 });

db.settings.createIndex({ key: 1 }, { unique: true });
db.settings.createIndex({ category: 1 });

db.profiles.createIndex({ discord_user_id: 1 }, { unique: true });

// Insert default settings
db.settings.insertMany([
    {
        key: 'risk.max_position_size',
        value: { amount: 1000, percentage: 10 },
        category: 'risk',
        updated_at: new Date()
    },
    {
        key: 'risk.max_positions_per_ticker',
        value: { count: 3 },
        category: 'risk',
        updated_at: new Date()
    },
    {
        key: 'trading.default_quantity',
        value: { contracts: 5 },
        category: 'trading',
        updated_at: new Date()
    },
    {
        key: 'trading.price_buffer',
        value: { percentage: 2 },
        category: 'trading',
        updated_at: new Date()
    },
    {
        key: 'OCO.profit_target',
        value: { percentage: 50 },
        category: 'OCO',
        updated_at: new Date()
    },
    {
        key: 'OCO.stop_loss',
        value: { percentage: 30 },
        category: 'OCO',
        updated_at: new Date()
    }
]);

print('MongoDB initialization complete');