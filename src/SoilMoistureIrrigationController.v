`default_nettype none

module tt_um_ultrasage_danz (
    input wire clk,
    input wire rst_n,           // active-low reset
    input wire ena,             // enable signal
    input wire [7:0] ui_in,     // Dedicated inputs
    input wire [7:0] uio_in,    // IOs: Input path
    output wire [7:0] uo_out,   // Dedicated outputs
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe    // IOs: Enable path
);

    // Extract your design inputs from the standard interface
    wire comp0 = ui_in[0];
    wire comp1 = ui_in[1];
    
    // Internal signals
    wire pump;
    wire invalid_flag;
    
    // Connect internal signals to outputs
    assign uo_out = {6'b0, invalid_flag, pump};
    assign uio_out = 8'b0;
    assign uio_oe = 8'b0;
    
    // Convert active-low reset to active-high for your state machine
    wire rst = ~rst_n;

    // ─── Comparator Encoding ───────────────────────────────────────────
    // {comp1, comp0} = 2'b00 → V < Vref_low → DRY → IRRIGATE
    // {comp1, comp0} = 2'b01 → Vref_low < V < Vref_high → MILD → IDLE
    // {comp1, comp0} = 2'b11 → V > Vref_high → WET → SATURATED
    // {comp1, comp0} = 2'b10 → INVALID (impossible comparator state)
    // ───────────────────────────────────────────────────────────────────

    wire [1:0] moisture_content;
    assign moisture_content = {comp1, comp0};

    // State encoding
    localparam [1:0] IDLE = 2'b00,
                     IRRIGATE = 2'b01,
                     SATURATED = 2'b10,
                     INVALID = 2'b11;

    reg [1:0] current_state, next_state;

    // ─── State Memory (Synchronous Reset) ─────────────────────────────
    always @(posedge clk) begin
        if (rst)
            current_state <= IDLE;
        else
            current_state <= next_state;
    end

    // ─── Next State Logic ──────────────────────────────────────────────
    always @(*) begin
        // Default: hold current state
        next_state = current_state;

        case (current_state)

            IDLE: begin 
                if (moisture_content == 2'b10) next_state = INVALID;  // Invalid comparator
                else if (moisture_content == 2'b00) next_state = IRRIGATE;
                else if (moisture_content == 2'b01) next_state = IDLE;
                else next_state = SATURATED;
            end

            IRRIGATE: begin
                case (moisture_content)
                    2'b10: next_state = INVALID; // Invalid comparator
                    2'b00: next_state = IRRIGATE; // Still dry → keep pumping
                    2'b01: next_state = IDLE; // Reached mild → idle
                    2'b11: next_state = SATURATED; // Overshot → saturated
                    default: next_state = INVALID;
                endcase
            end

            SATURATED: begin
                case (moisture_content)
                    2'b10: next_state = INVALID; // Invalid comparator
                    2'b11: next_state = SATURATED; // Still wet → stay
                    2'b01: next_state = IDLE; // Dried to mild → idle
                    2'b00: next_state = IRRIGATE; // Dried to low → irrigate
                    default: next_state = INVALID;
                endcase
            end

            INVALID: begin
                // Only escape on reset; hold until RST clears the fault
                if (moisture_content != 2'b10)
                    next_state = IDLE; // Comparators back to valid → recover
                else
                    next_state = INVALID;
            end

            default: next_state = IDLE;

        endcase
    end

    // ─── Output Logic (Moore) ─────────────────────────────────────────
    reg pump_internal, invalid_flag_internal;
    always @(*) begin
        // Safe defaults
        pump_internal = 1'b0;
        invalid_flag_internal = 1'b0;

        case (current_state)
            IDLE: begin pump_internal = 1'b0; invalid_flag_internal = 1'b0; end
            IRRIGATE: begin pump_internal = 1'b1; invalid_flag_internal = 1'b0; end // Pump ON
            SATURATED: begin pump_internal = 1'b0; invalid_flag_internal = 1'b0; end // Pump OFF
            INVALID: begin pump_internal = 1'b0; invalid_flag_internal = 1'b1; end // Flag fault
            default: begin pump_internal = 1'b0; invalid_flag_internal = 1'b0; end
        endcase
    end

    
    assign pump = pump_internal;
    assign invalid_flag = invalid_flag_internal;

endmodule
