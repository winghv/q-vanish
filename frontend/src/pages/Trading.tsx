import React, { useState, useEffect } from 'react';
import { getPositions, getOrders, placeOrder, Position, TradeOrder, PlaceOrderData } from '../services/api';

const Trading: React.FC = () => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [orders, setOrders] = useState<TradeOrder[]>([]);
  const [activeTab, setActiveTab] = useState<'manual' | 'strategy'>('manual');
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [symbol, setSymbol] = useState('');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // 加载持仓和订单
  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [pos, ord] = await Promise.all([
        getPositions(),
        getOrders()
      ]);
      setPositions(pos);
      setOrders(ord);
    } catch (err) {
      // 可加全局通知
      window.showNotification?.('获取数据失败', 'error');
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol || !quantity) return;
    setIsSubmitting(true);
    try {
      const data: PlaceOrderData = {
        symbol: symbol.toUpperCase(),
        type: 'buy', // 只实现买入，卖出可扩展
        quantity: Number(quantity),
        order_type: orderType,
        ...(orderType === 'limit' ? { price: Number(price) } : {})
      };
      await placeOrder(data);
      window.showNotification?.('下单成功', 'success');
      setSymbol('');
      setQuantity('');
      setPrice('');
      // 下单后刷新
      fetchData();
    } catch (err: any) {
      window.showNotification?.(err.response?.data?.detail || '下单失败', 'error');
    }
    setIsSubmitting(false);
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">实盘交易</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 交易表单 */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b">
              <div className="flex">
                <button
                  className={`flex-1 py-2 text-center ${activeTab === 'manual' ? 'text-blue-600 border-b-2 border-blue-600 font-medium' : 'text-gray-500 hover:text-gray-700'}`}
                  onClick={() => setActiveTab('manual')}
                >
                  手动交易
                </button>
                <button
                  className={`flex-1 py-2 text-center ${activeTab === 'strategy' ? 'text-blue-600 border-b-2 border-blue-600 font-medium' : 'text-gray-500 hover:text-gray-700'}`}
                  onClick={() => setActiveTab('strategy')}
                >
                  策略交易
                </button>
              </div>
            </div>
            <div className="p-4">
              {activeTab === 'manual' ? (
                <form onSubmit={handleSubmitOrder}>
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      交易类型
                    </label>
                    <div className="flex rounded-md shadow-sm">
                      <button
                        type="button"
                        className={`flex-1 py-2 text-center ${orderType === 'market' ? 'bg-blue-50 text-blue-700 font-medium' : 'bg-white text-gray-500'} border border-gray-300 rounded-l-md`}
                        onClick={() => setOrderType('market')}
                      >
                        市价单
                      </button>
                      <button
                        type="button"
                        className={`flex-1 py-2 text-center ${orderType === 'limit' ? 'bg-blue-50 text-blue-700 font-medium' : 'bg-white text-gray-500'} border border-gray-300 rounded-r-md border-l-0`}
                        onClick={() => setOrderType('limit')}
                      >
                        限价单
                      </button>
                    </div>
                  </div>
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      股票代码
                    </label>
                    <input
                      type="text"
                      placeholder="例如: AAPL"
                      value={symbol}
                      onChange={(e) => setSymbol(e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded"
                      required
                    />
                  </div>
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      数量
                    </label>
                    <input
                      type="number"
                      placeholder="输入数量"
                      value={quantity}
                      onChange={(e) => setQuantity(e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded"
                      min="1"
                      required
                    />
                  </div>
                  {orderType === 'limit' && (
                    <div className="mb-4">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        限价
                      </label>
                      <input
                        type="number"
                        placeholder="输入价格"
                        value={price}
                        onChange={(e) => setPrice(e.target.value)}
                        className="w-full p-2 border border-gray-300 rounded"
                        min="0.01"
                        step="0.01"
                        required={orderType === 'limit'}
                      />
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-2 mb-4">
                    <button
                      type="submit"
                      className="py-2 px-4 bg-green-600 text-white rounded hover:bg-green-700 transition"
                      disabled={isSubmitting}
                    >
                      {isSubmitting ? '提交中...' : '买入'}
                    </button>
                    <button
                      type="button"
                      className="py-2 px-4 bg-red-600 text-white rounded hover:bg-red-700 transition"
                      disabled={isSubmitting}
                    >
                      卖出
                    </button>
                  </div>
                </form>
              ) : (
                <div>
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      选择策略
                    </label>
                    <select className="w-full p-2 border border-gray-300 rounded">
                      <option value="">选择已创建的策略</option>
                      <option value="strategy1">均线交叉策略</option>
                      <option value="strategy2">RSI反转策略</option>
                      <option value="strategy3">布林带突破策略</option>
                    </select>
                  </div>
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      初始资金
                    </label>
                    <input
                      type="number"
                      placeholder="输入初始资金"
                      className="w-full p-2 border border-gray-300 rounded"
                      min="1000"
                    />
                  </div>
                  <button
                    type="button"
                    className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
                  >
                    启动策略交易
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
        {/* 持仓和订单 */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-semibold">当前持仓</h2>
            </div>
            <div className="overflow-x-auto">
              {isLoading ? (
                <div className="p-6 text-gray-400">加载中...</div>
              ) : (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">股票</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">数量</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">均价</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">现价</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">市值</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">盈亏</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {positions.map((position) => (
                      <tr key={position.symbol}>
                        <td className="px-6 py-4 whitespace-nowrap font-medium">{position.symbol}</td>
                        <td className="px-6 py-4 whitespace-nowrap">{position.quantity}</td>
                        <td className="px-6 py-4 whitespace-nowrap">${position.avg_cost.toFixed(2)}</td>
                        <td className="px-6 py-4 whitespace-nowrap">${position.current_price.toFixed(2)}</td>
                        <td className="px-6 py-4 whitespace-nowrap">${position.value.toFixed(2)}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={position.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}>
                            ${position.profit_loss.toFixed(2)} ({position.profit_loss_percent >= 0 ? '+' : ''}{position.profit_loss_percent.toFixed(2)}%)
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-semibold">订单历史</h2>
            </div>
            <div className="overflow-x-auto">
              {isLoading ? (
                <div className="p-6 text-gray-400">加载中...</div>
              ) : (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">订单ID</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">股票</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">类型</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">数量</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">价格</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">总额</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">时间</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {orders.map((order) => (
                      <tr key={order.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">{order.id}</td>
                        <td className="px-6 py-4 whitespace-nowrap font-medium">{order.symbol}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={order.type === 'buy' ? 'text-green-600' : 'text-red-600'}>
                            {order.type === 'buy' ? '买入' : '卖出'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            order.status === 'filled' ? 'bg-green-100 text-green-800' : 
                            order.status === 'pending' ? 'bg-yellow-100 text-yellow-800' : 
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {order.status === 'filled' ? '已成交' : order.status === 'pending' ? '待成交' : '已取消'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">{order.quantity}</td>
                        <td className="px-6 py-4 whitespace-nowrap">${order.price.toFixed(2)}</td>
                        <td className="px-6 py-4 whitespace-nowrap">${order.total.toFixed(2)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{order.timestamp}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Trading; 