/**
 * 店舗切替の共通モジュール。
 * 選択中の店舗IDを localStorage に保持し、axios の全APIリクエストに
 * `store` クエリパラメータを自動付与する。
 */
import axios from "axios";
import { API } from "./api";

export type StoreInfo = {
  id: string;
  name: string;
  short_name: string;
  has_data: boolean;
  is_default: boolean;
};

export const DEFAULT_STORE_ID = "maruhan_kamata7";

/** /api/stores が取得できない場合のフォールバック */
export const FALLBACK_STORES: StoreInfo[] = [
  {
    id: "maruhan_kamata7",
    name: "マルハンメガシティ2000蒲田7",
    short_name: "蒲田7",
    has_data: true,
    is_default: true,
  },
  {
    id: "bigdipper_togoshiginza",
    name: "BIGディッパー戸越銀座",
    short_name: "戸越銀座",
    has_data: false,
    is_default: false,
  },
];

const STORAGE_KEY = "sumaslo_store_id";

export function getStoreId(): string {
  if (typeof window === "undefined") return DEFAULT_STORE_ID;
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_STORE_ID;
}

/** 店舗を切り替えてリロード（全ページのデータを再取得するため） */
export function switchStore(id: string): void {
  localStorage.setItem(STORAGE_KEY, id);
  window.location.reload();
}

/** 素の fetch 用: URLに store パラメータを付与する */
export function withStore(url: string): string {
  return `${url}${url.includes("?") ? "&" : "?"}store=${getStoreId()}`;
}

let interceptorInstalled = false;

/** axios の全APIリクエストに store パラメータを自動付与する（layoutから1回呼ぶ） */
export function installStoreInterceptor(): void {
  if (interceptorInstalled) return;
  interceptorInstalled = true;
  axios.interceptors.request.use((config) => {
    const url = config.url ?? "";
    if (url.startsWith(API)) {
      config.params = { ...(config.params ?? {}), store: getStoreId() };
    }
    return config;
  });
}
