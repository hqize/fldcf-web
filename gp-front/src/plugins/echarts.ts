/**
 * 在入口注册后，业务组件通过 inject(echartsKey) 使用，避免各页面重复 import 'echarts'。
 */
import * as echarts from 'echarts'
import type { InjectionKey } from 'vue'

export type EChartsNS = typeof echarts
export const echartsKey: InjectionKey<EChartsNS> = Symbol('echarts')

export { echarts }
export type { EChartsOption } from 'echarts'
