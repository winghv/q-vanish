import { Bars3Icon, BellIcon, UserCircleIcon } from '@heroicons/react/24/outline';
import { Link } from 'react-router-dom';
import { useState } from 'react';

interface HeaderProps {
  setSidebarOpen: (open: boolean) => void;
}

const Header: React.FC<HeaderProps> = ({ setSidebarOpen }) => {
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);

  return (
    <header className="sticky top-0 bg-white border-b border-secondary-200 z-30">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left side */}
          <div className="flex items-center">
            {/* Hamburger button */}
            <button
              className="text-secondary-500 hover:text-secondary-600 lg:hidden"
              onClick={() => setSidebarOpen(true)}
              aria-controls="sidebar"
              aria-expanded="false"
            >
              <span className="sr-only">打开侧边栏</span>
              <Bars3Icon className="w-6 h-6" />
            </button>
          </div>

          {/* Logo */}
          <Link to="/" className="block lg:hidden">
            <div className="flex items-center">
              <span className="text-lg font-semibold text-primary-600">Q-Vanish</span>
            </div>
          </Link>

          {/* Right side */}
          <div className="flex items-center space-x-3">
            {/* Notifications */}
            <div className="relative">
              <button
                className="p-2 text-secondary-500 rounded-full hover:text-secondary-600 hover:bg-secondary-100"
                onClick={() => setNotificationsOpen(!notificationsOpen)}
              >
                <span className="sr-only">消息通知</span>
                <BellIcon className="w-6 h-6" />
                <div className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full"></div>
              </button>
              {notificationsOpen && (
                <div className="absolute right-0 w-80 mt-2 bg-white border border-secondary-200 rounded-lg shadow-lg">
                  <div className="p-4 border-b border-secondary-200">
                    <h2 className="text-lg font-medium">通知</h2>
                  </div>
                  <div className="p-2">
                    <div className="p-3 hover:bg-secondary-50 rounded-lg cursor-pointer">
                      <p className="text-sm font-medium">策略警报：移动平均线交叉</p>
                      <p className="text-xs text-secondary-500">10分钟前</p>
                    </div>
                    <div className="p-3 hover:bg-secondary-50 rounded-lg cursor-pointer">
                      <p className="text-sm font-medium">回测完成：双均线策略</p>
                      <p className="text-xs text-secondary-500">1小时前</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* User */}
            <div className="relative">
              <button
                className="flex items-center p-2 text-secondary-500 rounded-full hover:text-secondary-600 hover:bg-secondary-100"
                onClick={() => setUserOpen(!userOpen)}
              >
                <span className="sr-only">用户菜单</span>
                <UserCircleIcon className="w-6 h-6" />
              </button>
              {userOpen && (
                <div className="absolute right-0 w-48 mt-2 bg-white border border-secondary-200 rounded-lg shadow-lg">
                  <div className="p-3 border-b border-secondary-200">
                    <p className="text-sm font-medium">用户名</p>
                    <p className="text-xs text-secondary-500">user@example.com</p>
                  </div>
                  <div className="p-2">
                    <Link
                      to="/settings"
                      className="block px-4 py-2 text-sm text-secondary-700 hover:bg-secondary-100 rounded-md"
                      onClick={() => setUserOpen(false)}
                    >
                      设置
                    </Link>
                    <button
                      className="block w-full text-left px-4 py-2 text-sm text-secondary-700 hover:bg-secondary-100 rounded-md"
                    >
                      退出登录
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header; 