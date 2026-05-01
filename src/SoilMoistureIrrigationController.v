module moisture_irrigation (
    input wire clk,
    input wire rst, // Synchronous, active-high reset
    input wire comp0,
    input wire comp1,
    output reg pump,
    output reg invalid_flag
);

    // ─── Comparator Encoding ───────────────────────────────────────────
    // {comp1, comp0} = 2'b00 → V < Vref_low → DRY → IRRIGATE
    // {comp1, comp0} = 2'b01 → Vref_low < V < Vref_high → MILD → IDLE
    // {comp1, comp0} = 2'b11 → V > Vref_high → WET → SATURATED
    // {comp1, comp0} = 2'b10 → INVALID (impossible comparator state)
    // ──────────────────────────────────────────────────────────────────

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
                if (invalid) next_state = INVALID;
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
    always @(*) begin
        // Safe defaults
        pump = 1'b0;
        invalid_flag = 1'b0;

        case (current_state)
            IDLE: begin pump = 1'b0; invalid_flag = 1'b0; end
            IRRIGATE: begin pump = 1'b1; invalid_flag = 1'b0; end // Pump ON
            SATURATED: begin pump = 1'b0; invalid_flag = 1'b0; end // Pump OFF
            INVALID: begin pump = 1'b0; invalid_flag = 1'b1; end // Flag fault
            default: begin pump = 1'b0; invalid_flag = 1'b0; end
        endcase
    end

endmodule
