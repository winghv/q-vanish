import React, { useState } from 'react';

interface UserProfile {
  name: string;
  email: string;
  avatar: string;
}

interface NotificationSettings {
  emailAlerts: boolean;
  tradingAlerts: boolean;
  marketUpdates: boolean;
  weeklyReports: boolean;
}

interface ApiKeys {
  provider: string;
  key: string;
  status: 'active' | 'inactive';
  lastUsed: string;
}

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'profile' | 'notifications' | 'api' | 'privacy'>('profile');
  
  const [profile, setProfile] = useState<UserProfile>({
    name: '张三',
    email: 'zhang.san@example.com',
    avatar: '',
  });
  
  const [notifications, setNotifications] = useState<NotificationSettings>({
    emailAlerts: true,
    tradingAlerts: true,
    marketUpdates: false,
    weeklyReports: true,
  });
  
  const [apiKeys, setApiKeys] = useState<ApiKeys[]>([
    {
      provider: 'Yahoo Finance',
      key: 'yfin_xxxx_xxxx_xxxx',
      status: 'active',
      lastUsed: '2023-06-15',
    },
    {
      provider: 'Alpha Vantage',
      key: 'av_xxxx_xxxx_xxxx',
      status: 'inactive',
      lastUsed: '2023-05-20',
    },
  ]);
  
  const handleProfileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setProfile({ ...profile, [name]: value });
  };
  
  const handleNotificationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    setNotifications({ ...notifications, [name]: checked });
  };
  
  const toggleApiKeyStatus = (index: number) => {
    const updatedKeys = [...apiKeys];
    updatedKeys[index].status = updatedKeys[index].status === 'active' ? 'inactive' : 'active';
    setApiKeys(updatedKeys);
  };
  
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">设置</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* 侧边标签栏 */}
        <div className="md:col-span-1">
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b">
              <h2 className="text-lg font-medium">设置选项</h2>
            </div>
            <div className="p-2">
              <button
                className={`w-full text-left p-3 rounded ${activeTab === 'profile' ? 'bg-blue-50 text-blue-600' : 'hover:bg-gray-50'}`}
                onClick={() => setActiveTab('profile')}
              >
                个人资料
              </button>
              <button
                className={`w-full text-left p-3 rounded ${activeTab === 'notifications' ? 'bg-blue-50 text-blue-600' : 'hover:bg-gray-50'}`}
                onClick={() => setActiveTab('notifications')}
              >
                通知设置
              </button>
              <button
                className={`w-full text-left p-3 rounded ${activeTab === 'api' ? 'bg-blue-50 text-blue-600' : 'hover:bg-gray-50'}`}
                onClick={() => setActiveTab('api')}
              >
                API密钥
              </button>
              <button
                className={`w-full text-left p-3 rounded ${activeTab === 'privacy' ? 'bg-blue-50 text-blue-600' : 'hover:bg-gray-50'}`}
                onClick={() => setActiveTab('privacy')}
              >
                隐私与安全
              </button>
            </div>
          </div>
        </div>
        
        {/* 设置内容 */}
        <div className="md:col-span-3">
          <div className="bg-white rounded-lg shadow">
            {/* 个人资料设置 */}
            {activeTab === 'profile' && (
              <div>
                <div className="px-6 py-4 border-b">
                  <h2 className="text-lg font-medium">个人资料</h2>
                </div>
                <div className="p-6">
                  <div className="mb-6">
                    <div className="flex items-center mb-4">
                      <div className="w-16 h-16 rounded-full bg-gray-200 mr-4 flex items-center justify-center text-gray-500">
                        {profile.avatar ? (
                          <img src={profile.avatar} alt="Avatar" className="w-full h-full rounded-full" />
                        ) : (
                          <span className="text-2xl">{profile.name.charAt(0)}</span>
                        )}
                      </div>
                      <div>
                        <button className="bg-blue-600 text-white py-1 px-3 rounded text-sm hover:bg-blue-700 transition">
                          更改头像
                        </button>
                      </div>
                    </div>
                  </div>
                  
                  <form>
                    <div className="grid grid-cols-1 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          姓名
                        </label>
                        <input
                          type="text"
                          name="name"
                          value={profile.name}
                          onChange={handleProfileChange}
                          className="w-full p-2 border border-gray-300 rounded"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          电子邮件
                        </label>
                        <input
                          type="email"
                          name="email"
                          value={profile.email}
                          onChange={handleProfileChange}
                          className="w-full p-2 border border-gray-300 rounded"
                        />
                      </div>
                      
                      <div>
                        <button
                          type="button"
                          className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition"
                        >
                          保存修改
                        </button>
                      </div>
                    </div>
                  </form>
                </div>
              </div>
            )}
            
            {/* 通知设置 */}
            {activeTab === 'notifications' && (
              <div>
                <div className="px-6 py-4 border-b">
                  <h2 className="text-lg font-medium">通知设置</h2>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between py-2">
                      <div>
                        <h3 className="text-sm font-medium text-gray-900">邮件提醒</h3>
                        <p className="text-sm text-gray-500">接收关于账户活动的邮件提醒</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          name="emailAlerts"
                          checked={notifications.emailAlerts}
                          onChange={handleNotificationChange}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                    
                    <div className="flex items-center justify-between py-2">
                      <div>
                        <h3 className="text-sm font-medium text-gray-900">交易提醒</h3>
                        <p className="text-sm text-gray-500">接收交易执行和订单状态的提醒</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          name="tradingAlerts"
                          checked={notifications.tradingAlerts}
                          onChange={handleNotificationChange}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                    
                    <div className="flex items-center justify-between py-2">
                      <div>
                        <h3 className="text-sm font-medium text-gray-900">市场更新</h3>
                        <p className="text-sm text-gray-500">接收市场变动和新闻的更新</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          name="marketUpdates"
                          checked={notifications.marketUpdates}
                          onChange={handleNotificationChange}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                    
                    <div className="flex items-center justify-between py-2">
                      <div>
                        <h3 className="text-sm font-medium text-gray-900">周报</h3>
                        <p className="text-sm text-gray-500">接收每周的投资组合表现报告</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          name="weeklyReports"
                          checked={notifications.weeklyReports}
                          onChange={handleNotificationChange}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                      </label>
                    </div>
                    
                    <div className="pt-4">
                      <button
                        type="button"
                        className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition"
                      >
                        保存设置
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* API密钥管理 */}
            {activeTab === 'api' && (
              <div>
                <div className="px-6 py-4 border-b">
                  <h2 className="text-lg font-medium">API密钥管理</h2>
                </div>
                <div className="p-6">
                  <div className="mb-6">
                    <p className="text-sm text-gray-500 mb-4">
                      管理您用于连接外部数据源和交易服务的API密钥。
                    </p>
                    
                    <button
                      type="button"
                      className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition mb-6"
                    >
                      添加新API密钥
                    </button>
                    
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">提供商</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">密钥</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">最后使用</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {apiKeys.map((key, index) => (
                            <tr key={index}>
                              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{key.provider}</td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{key.key}</td>
                              <td className="px-6 py-4 whitespace-nowrap">
                                <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                  key.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                                }`}>
                                  {key.status === 'active' ? '已启用' : '已禁用'}
                                </span>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{key.lastUsed}</td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                <button
                                  className="text-blue-600 hover:text-blue-900 mr-3"
                                  onClick={() => toggleApiKeyStatus(index)}
                                >
                                  {key.status === 'active' ? '禁用' : '启用'}
                                </button>
                                <button className="text-red-600 hover:text-red-900">
                                  删除
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* 隐私与安全 */}
            {activeTab === 'privacy' && (
              <div>
                <div className="px-6 py-4 border-b">
                  <h2 className="text-lg font-medium">隐私与安全</h2>
                </div>
                <div className="p-6">
                  <div className="mb-6">
                    <h3 className="text-md font-medium mb-3">修改密码</h3>
                    <form className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          当前密码
                        </label>
                        <input
                          type="password"
                          className="w-full p-2 border border-gray-300 rounded"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          新密码
                        </label>
                        <input
                          type="password"
                          className="w-full p-2 border border-gray-300 rounded"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          确认新密码
                        </label>
                        <input
                          type="password"
                          className="w-full p-2 border border-gray-300 rounded"
                        />
                      </div>
                      <div>
                        <button
                          type="button"
                          className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition"
                        >
                          更新密码
                        </button>
                      </div>
                    </form>
                  </div>
                  
                  <div className="mb-6 pt-6 border-t">
                    <h3 className="text-md font-medium mb-3">双因素认证</h3>
                    <p className="text-sm text-gray-500 mb-4">
                      启用双因素认证以提高您账户的安全性。
                    </p>
                    <button
                      type="button"
                      className="bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700 transition"
                    >
                      启用双因素认证
                    </button>
                  </div>
                  
                  <div className="pt-6 border-t">
                    <h3 className="text-md font-medium mb-3 text-red-600">危险区域</h3>
                    <p className="text-sm text-gray-500 mb-4">
                      一旦删除账户，所有数据将永久丢失，且无法恢复。
                    </p>
                    <button
                      type="button"
                      className="bg-red-600 text-white py-2 px-4 rounded hover:bg-red-700 transition"
                    >
                      删除我的账户
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings; 