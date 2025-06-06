import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  ChartBarIcon,
  ArrowPathIcon,
  PlayIcon,
  FolderIcon,
  SparklesIcon,
  Cog6ToothIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import classNames from 'classnames';

interface SidebarProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

const navigation = [
  { name: '仪表盘', href: '/dashboard', icon: HomeIcon },
  { name: '交易策略', href: '/strategies', icon: ChartBarIcon },
  { name: '策略回测', href: '/backtest', icon: ArrowPathIcon },
  { name: '实盘交易', href: '/trading', icon: PlayIcon },
  { name: '投资组合', href: '/portfolio', icon: FolderIcon },
  { name: 'AI助手', href: '/ai-assistant', icon: SparklesIcon },
  { name: '设置', href: '/settings', icon: Cog6ToothIcon },
];

const Sidebar: React.FC<SidebarProps> = ({ sidebarOpen, setSidebarOpen }) => {
  const location = useLocation();
  
  // 添加滚动锁定效果
  useEffect(() => {
    if (sidebarOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [sidebarOpen]);

  return (
    <>
      {/* Mobile sidebar */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          {/* Overlay */}
          <div 
            className="fixed inset-0 bg-secondary-600 bg-opacity-75"
            onClick={() => setSidebarOpen(false)}
          />
          
          {/* Sidebar */}
          <div className="relative flex flex-col flex-1 w-full max-w-xs bg-white">
            {/* Close button */}
            <div className="absolute top-0 right-0 pt-2 mr-2">
              <button
                className="flex items-center justify-center w-10 h-10 rounded-md text-secondary-400 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500"
                onClick={() => setSidebarOpen(false)}
              >
                <span className="sr-only">关闭侧边栏</span>
                <XMarkIcon className="w-6 h-6" aria-hidden="true" />
              </button>
            </div>
            
            {/* Logo */}
            <div className="flex items-center h-16 px-6 border-b border-secondary-200">
              <Link to="/" className="flex items-center">
                <span className="text-xl font-semibold text-primary-600">Q-Vanish</span>
              </Link>
            </div>
            
            {/* Navigation */}
            <div className="flex-1 h-0 overflow-y-auto">
              <nav className="px-3 py-4">
                <div className="space-y-1">
                  {navigation.map((item) => (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={classNames(
                        location.pathname.startsWith(item.href)
                          ? 'bg-primary-100 text-primary-900'
                          : 'text-secondary-700 hover:bg-secondary-100',
                        'group flex items-center py-2 px-3 text-base font-medium rounded-md'
                      )}
                    >
                      <item.icon
                        className={classNames(
                          location.pathname.startsWith(item.href)
                            ? 'text-primary-500'
                            : 'text-secondary-500 group-hover:text-secondary-900',
                          'mr-4 flex-shrink-0 h-6 w-6'
                        )}
                        aria-hidden="true"
                      />
                      {item.name}
                    </Link>
                  ))}
                </div>
              </nav>
            </div>
          </div>
        </div>
      )}

      {/* Desktop sidebar */}
      <div className="hidden lg:flex lg:flex-shrink-0">
        <div className="flex flex-col w-64">
          <div className="flex flex-col flex-1 min-h-0 border-r border-secondary-200 bg-white">
            {/* Logo */}
            <div className="flex items-center h-16 px-6 border-b border-secondary-200">
              <Link to="/" className="flex items-center">
                <span className="text-xl font-semibold text-primary-600">Q-Vanish</span>
              </Link>
            </div>
            
            {/* Navigation */}
            <div className="flex flex-col flex-1 pt-5 pb-4 overflow-y-auto">
              <nav className="flex-1 px-3">
                <div className="space-y-1">
                  {navigation.map((item) => (
                    <Link
                      key={item.name}
                      to={item.href}
                      className={classNames(
                        location.pathname.startsWith(item.href)
                          ? 'bg-primary-100 text-primary-900'
                          : 'text-secondary-700 hover:bg-secondary-100',
                        'group flex items-center py-2 px-3 text-base font-medium rounded-md'
                      )}
                    >
                      <item.icon
                        className={classNames(
                          location.pathname.startsWith(item.href)
                            ? 'text-primary-500'
                            : 'text-secondary-500 group-hover:text-secondary-900',
                          'mr-4 flex-shrink-0 h-6 w-6'
                        )}
                        aria-hidden="true"
                      />
                      {item.name}
                    </Link>
                  ))}
                </div>
              </nav>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar; 