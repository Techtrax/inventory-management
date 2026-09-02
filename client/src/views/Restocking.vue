<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card budget-card">
      <div class="budget-header">
        <label class="budget-label" for="budget-slider">{{ t('restocking.budgetLabel') }}</label>
        <span class="budget-value">{{ currencySymbol }}{{ budget.toLocaleString() }}</span>
      </div>
      <input
        id="budget-slider"
        type="range"
        min="0"
        max="6000"
        step="100"
        v-model.number="budget"
        class="budget-slider"
      />
    </div>

    <div v-if="loadingRecommendations" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="recommendationsError" class="error">{{ recommendationsError }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.itemsRecommended') }}</div>
          <div class="stat-value">{{ itemsRecommendedCount }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.budgetUsed') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ totalCost.toLocaleString() }}</div>
          <div class="stat-sublabel">{{ budgetUsedPercent }}%</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.budgetRemaining') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ budgetRemaining.toLocaleString() }}</div>
        </div>
      </div>

      <div class="progress-track">
        <div class="progress-fill" :style="{ width: progressWidth + '%' }"></div>
      </div>

      <div v-if="confirmation" class="card confirmation-card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.orderPlaced') }}</h3>
        </div>
        <div class="confirmation-body">
          <div class="confirmation-row">
            <span class="confirmation-label">{{ t('restocking.orderNumber') }}</span>
            <span class="confirmation-value">{{ confirmation.order_number }}</span>
          </div>
          <div class="confirmation-row">
            <span class="confirmation-label">{{ t('restocking.expectedDelivery') }}</span>
            <span class="confirmation-value">{{ formatDate(confirmation.expected_delivery) }}</span>
          </div>
          <div class="confirmation-row">
            <span class="confirmation-label">{{ t('restocking.leadTimeDays', { days: confirmation.lead_time_days }) }}</span>
          </div>
        </div>
      </div>

      <div v-if="orderError" class="error">{{ orderError }}</div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedItems') }}</h3>
          <button
            class="place-order-btn"
            :disabled="recommendations.length === 0 || placingOrder"
            @click="placeOrder"
          >
            {{ placingOrder ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="recommendations.length === 0" class="empty-state">
          {{ t('restocking.noRecommendations') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th>{{ t('restocking.table.currentDemand') }}</th>
                <th>{{ t('restocking.table.forecastedDemand') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineTotal') }}</th>
                <th>{{ t('restocking.table.priority') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendations" :key="item.item_sku">
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td>
                  <span :class="['badge', item.trend]">
                    {{ t('trends.' + item.trend) }}
                  </span>
                </td>
                <td>{{ item.current_demand }}</td>
                <td>{{ item.forecasted_demand }}</td>
                <td>{{ item.quantity }}</td>
                <td>{{ currencySymbol }}{{ item.unit_cost.toFixed(2) }}</td>
                <td><strong>{{ currencySymbol }}{{ item.line_total.toFixed(2) }}</strong></td>
                <td>
                  <span :class="['badge', priorityBadgeClass(item.priority_reason)]">
                    {{ t('restocking.priorityReason.' + item.priority_reason) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const budget = ref(4000)

    const loadingRecommendations = ref(true)
    const recommendationsError = ref(null)
    const recommendations = ref([])
    const totalCost = ref(0)
    const budgetRemaining = ref(0)
    const itemsRecommendedCount = ref(0)

    const placingOrder = ref(false)
    const orderError = ref(null)
    const confirmation = ref(null)

    let debounceTimer = null

    const budgetUsedPercent = computed(() => {
      if (!budget.value || budget.value <= 0) return 0
      return Math.round((totalCost.value / budget.value) * 100)
    })

    const progressWidth = computed(() => {
      if (!budget.value || budget.value <= 0) return 0
      return Math.min(100, (totalCost.value / budget.value) * 100)
    })

    const loadRecommendations = async () => {
      try {
        loadingRecommendations.value = true
        recommendationsError.value = null
        const response = await api.getRestockingRecommendations(budget.value)
        recommendations.value = response.recommendations
        totalCost.value = response.total_cost
        budgetRemaining.value = response.budget_remaining
        itemsRecommendedCount.value = response.items_recommended_count
      } catch (err) {
        recommendationsError.value = 'Failed to load restocking recommendations: ' + err.message
      } finally {
        loadingRecommendations.value = false
      }
    }

    watch(budget, () => {
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(loadRecommendations, 300)
    })

    const priorityBadgeClass = (reason) => {
      const map = {
        backlog: 'danger',
        below_reorder_point: 'warning',
        demand_growth: 'info'
      }
      return map[reason] || 'info'
    }

    const placeOrder = async () => {
      placingOrder.value = true
      orderError.value = null
      try {
        confirmation.value = await api.createRestockingOrder(budget.value)
        await loadRecommendations()
      } catch (err) {
        orderError.value = 'Failed to place restocking order: ' + err.message
      } finally {
        placingOrder.value = false
      }
    }

    const formatDate = (dateString) => {
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return new Date(dateString).toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    onMounted(loadRecommendations)

    return {
      t,
      currencySymbol,
      budget,
      loadingRecommendations,
      recommendationsError,
      recommendations,
      totalCost,
      budgetRemaining,
      itemsRecommendedCount,
      budgetUsedPercent,
      progressWidth,
      placingOrder,
      orderError,
      confirmation,
      priorityBadgeClass,
      placeOrder,
      formatDate
    }
  }
}
</script>

<style scoped>
.budget-card {
  margin-bottom: 1.5rem;
}

.budget-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.875rem;
}

.budget-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.budget-slider {
  width: 100%;
  accent-color: #2563eb;
  cursor: pointer;
}

.stat-sublabel {
  margin-top: 0.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
}

.progress-track {
  width: 100%;
  height: 10px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 1.5rem;
}

.progress-fill {
  height: 100%;
  background: #2563eb;
  border-radius: 999px;
  transition: width 0.3s ease;
}

.place-order-btn {
  background: #2563eb;
  color: white;
  border: none;
  padding: 0.625rem 1.25rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #64748b;
  font-size: 0.938rem;
}

.confirmation-card {
  border-left: 4px solid #10b981;
}

.confirmation-body {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.confirmation-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.confirmation-label {
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 500;
}

.confirmation-value {
  color: #0f172a;
  font-weight: 700;
  font-size: 0.938rem;
}
</style>
